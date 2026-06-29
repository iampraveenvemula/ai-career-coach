"""
LLM-powered resume builder service.

Uses Ollama to restructure + keyword-align the candidate's resume for a target role,
then exports it as a formatted DOCX using python-docx.
"""
import re
import os
import io
import httpx
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: F401

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

STRUCTURE_PROMPT = """You are an expert resume writer. You will be given a candidate's raw resume
and a job description. Your task is to produce a clean, ATS-optimised, 1–2 page resume in
plain text with exactly the following four sections in this order:

PROFESSIONAL SUMMARY
SKILLS
EXPERIENCE
EDUCATION

---

SECTION RULES:

PROFESSIONAL SUMMARY
- Write 2–4 sentences that position the candidate for THIS specific role.
- Reference the job title and 1–2 key requirements from the JD.
- Draw only on facts present in the resume. Do NOT invent experience.

SKILLS
- List ALL technical and professional skills found in the candidate's resume.
- Group into sub-categories where appropriate, e.g.:
    Languages: Python, Java, SQL
    Frameworks: React, FastAPI, Django
    Tools & Platforms: AWS, Docker, Kubernetes, Git
    Soft Skills: Team Leadership, Agile, Cross-functional Collaboration
- Prioritise skills that appear in the job description by listing them first within each group.
- Do NOT add skills the candidate does not have.

EXPERIENCE
- Include EVERY job from the resume. Do NOT drop any role.
- Format each role exactly as:
    Company Name | Job Title | Start Month Year – End Month Year (or Present)
  followed by 3–5 bullet points starting with •
- Each bullet: strong action verb + specific accomplishment with metrics where available.
- Reword bullets to naturally incorporate JD keywords where the candidate's experience supports it.
- Do NOT fabricate metrics or responsibilities not in the original resume.

EDUCATION
- List degrees in reverse chronological order.
- Format: Degree, Field of Study | Institution | Year
- Keep it brief — 1–2 lines per degree.
- If there are certifications or relevant coursework, list them here on a separate line.

---

FORMATTING RULES (critical — the output is parsed by code):
- Section headers MUST be exactly: PROFESSIONAL SUMMARY, SKILLS, EXPERIENCE, EDUCATION (ALL-CAPS, no other text on that line)
- Job entry headers MUST use the pipe separator: Company | Title | Date
- Bullet points MUST start with • (bullet character)
- Blank lines between sections and between job entries
- Output ONLY the resume text. No markdown fences (no ```) no explanations, no preamble.
- First line of output is the candidate's full name (if found in resume), otherwise skip.
- Second line (if name present): contact info on one line, e.g.: email@example.com | LinkedIn | City, Country
"""

REFINE_PROMPT = """You are a precise resume line editor.

You are given a resume and a REFINEMENT INSTRUCTION that targets ONE specific line or bullet.
Apply the instruction to that line only and return the COMPLETE, UNCHANGED resume with just that line updated.

Strict rules:
- Change ONLY the specific line described in the instruction.
- DO NOT remove any other line, bullet, section, job, or project.
- DO NOT reorder anything.
- Preserve the exact formatting: ALL-CAPS headers, • bullets, | separators, blank lines.
- Output ONLY the full resume text. No explanations, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def build_tailored_resume_docx(
    resume_text: str,
    job_description: str,
    candidate_name: str = "",
    job_title: str = "",
    company: str = "",
) -> tuple[bytes, str]:
    """
    Structures + keyword-aligns the resume via LLM, then renders as DOCX.
    Returns (docx_bytes, filename).
    """
    if job_description:
        tailored_text = await _llm_rewrite(resume_text, job_description)
    else:
        tailored_text = resume_text
    return generate_docx_bytes(tailored_text, candidate_name, job_title, company)


async def _llm_rewrite(resume_text: str, job_description: str) -> str:
    """
    Single-pass LLM call that both restructures the resume into the canonical
    4-section format AND aligns keywords to the job description.
    """
    resume_truncated = resume_text[:5000] if len(resume_text) > 5000 else resume_text
    jd_truncated = job_description[:2000] if len(job_description) > 2000 else job_description

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": STRUCTURE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"CANDIDATE'S RESUME:\n{resume_truncated}\n\n"
                    f"JOB DESCRIPTION:\n{jd_truncated}"
                ),
            },
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()

    content = response.json().get("message", {}).get("content", "").strip()
    # Strip accidental markdown fences
    content = re.sub(r"^```(?:markdown|text)?|```$", "", content, flags=re.MULTILINE).strip()
    return content


async def _llm_refine(current_resume: str, instruction: str) -> str:
    """Apply a targeted refinement instruction to an already-tailored resume."""
    resume_truncated = current_resume[:6000] if len(current_resume) > 6000 else current_resume

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": REFINE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"CURRENT RESUME:\n{resume_truncated}\n\n"
                    f"REFINEMENT INSTRUCTION:\n{instruction}"
                ),
            },
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()

    content = response.json().get("message", {}).get("content", "").strip()
    content = re.sub(r"^```(?:markdown|text)?|```$", "", content, flags=re.MULTILINE).strip()
    return content


# ---------------------------------------------------------------------------
# DOCX generator
# ---------------------------------------------------------------------------

_SECTION_HEADERS = {
    "PROFESSIONAL SUMMARY", "SUMMARY",
    "WORK EXPERIENCE", "EXPERIENCE", "EMPLOYMENT",
    "PROJECTS", "PROJECT EXPERIENCE",
    "EDUCATION",
    "SKILLS", "TECHNICAL SKILLS",
    "CERTIFICATIONS", "AWARDS", "PUBLICATIONS", "VOLUNTEERING",
}

_COLOR_NAME     = RGBColor(0x1a, 0x1a, 0x2e)   # deep navy  — candidate name
_COLOR_SUBHEAD  = RGBColor(0x16, 0x21, 0x3e)   # dark blue  — section headers
_COLOR_COMPANY  = RGBColor(0x1a, 0x1a, 0x2e)   # near-black — company/role lines
_COLOR_META     = RGBColor(0x77, 0x77, 0x88)   # mid-grey   — dates, contact info
_COLOR_BODY     = RGBColor(0x40, 0x40, 0x40)   # dark grey  — body / bullets
_COLOR_RULE     = RGBColor(0xdd, 0xdd, 0xdd)   # light rule


def _safe(text: str) -> str:
    """Normalise common Unicode punctuation for DOCX compatibility."""
    return (
        text
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "–")
        .replace("\u2014", "—")
        .strip()
    )


def _add_rule(doc: Document, thin: bool = False) -> None:
    """Add a thin horizontal rule paragraph using paragraph border."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(3) if not thin else Pt(2)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4" if thin else "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "CCCCCC")
    pBdr.append(bottom)
    pPr.append(pBdr)


def generate_docx_bytes(
    tailored_text: str,
    candidate_name: str = "",
    job_title: str = "",
    company: str = "",
) -> tuple[bytes, str]:
    """
    Renders the structured plain-text resume as a polished DOCX.
    Returns (docx_bytes, smart_filename).
    """
    doc = Document()

    # Page margins — tight for 1-page fit
    for section in doc.sections:
        section.top_margin    = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin   = Inches(0.80)
        section.right_margin  = Inches(0.80)

    # Remove default empty paragraph
    if doc.paragraphs:
        p = doc.paragraphs[0]._element
        p.getparent().remove(p)

    lines = tailored_text.splitlines()
    first_content_line = True  # used to detect name / contact header lines

    for raw_line in lines:
        line = raw_line.rstrip()

        # Blank line → small spacer
        if not line.strip():
            sp = doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(2)
            continue

        stripped = _safe(line.strip())
        upper = stripped.upper()

        # ------------------------------------------------------------------
        # Section header (ALL-CAPS known keyword)
        # ------------------------------------------------------------------
        if upper in _SECTION_HEADERS or any(upper.startswith(h) for h in _SECTION_HEADERS):
            first_content_line = False
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after  = Pt(1)
            run = p.add_run(stripped.upper())
            run.font.size      = Pt(9.5)
            run.font.bold      = True
            run.font.color.rgb = _COLOR_SUBHEAD
            _add_rule(doc, thin=True)
            continue

        # ------------------------------------------------------------------
        # Candidate name (first non-empty line if no section header seen yet)
        # ------------------------------------------------------------------
        if first_content_line and not "|" in stripped and not stripped.startswith("•"):
            # Check if this looks like a name (no @ symbol, not too long)
            if "@" not in stripped and len(stripped.split()) <= 5 and len(stripped) < 60:
                first_content_line = False
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(1)
                run = p.add_run(stripped)
                run.font.size      = Pt(18)
                run.font.bold      = True
                run.font.color.rgb = _COLOR_NAME
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue

        # ------------------------------------------------------------------
        # Contact info line (email / LinkedIn / city — contains @ or |)
        # ------------------------------------------------------------------
        if first_content_line or (
            ("@" in stripped or "linkedin" in stripped.lower() or
             ("|" in stripped and not any(
                 kw in stripped.upper()
                 for kw in {"PRESENT", "JAN","FEB","MAR","APR","MAY","JUN",
                             "JUL","AUG","SEP","OCT","NOV","DEC"}) and
             len(stripped.split("|")) <= 3 and
             len(stripped) < 100))
        ):
            if "@" in stripped or "linkedin" in stripped.lower():
                first_content_line = False
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(stripped)
                run.font.size      = Pt(9)
                run.font.color.rgb = _COLOR_META
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue

        first_content_line = False

        # ------------------------------------------------------------------
        # Bullet point
        # ------------------------------------------------------------------
        if stripped.startswith(("•", "-", "*", "·")):
            bullet_text = stripped.lstrip("•-*· ").strip()
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.20)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(bullet_text)
            run.font.size      = Pt(10)
            run.font.color.rgb = _COLOR_BODY
            continue

        # ------------------------------------------------------------------
        # Company | Title | Date  (job entry header)
        # ------------------------------------------------------------------
        if "|" in stripped and len(stripped.split("|")) >= 2:
            parts = [s.strip() for s in stripped.split("|")]
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(7)
            p.paragraph_format.space_after  = Pt(1)
            # Company name bold
            r_company = p.add_run(parts[0])
            r_company.font.bold      = True
            r_company.font.size      = Pt(10.5)
            r_company.font.color.rgb = _COLOR_COMPANY
            # Role + dates in lighter weight
            if len(parts) > 1:
                r_rest = p.add_run("  ·  " + "  ·  ".join(parts[1:]))
                r_rest.font.size      = Pt(10)
                r_rest.font.color.rgb = _COLOR_META
            continue

        # ------------------------------------------------------------------
        # Project / sub-heading line (contains — or –)
        # ------------------------------------------------------------------
        if "—" in stripped or "–" in stripped:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(5)
            p.paragraph_format.space_after  = Pt(1)
            run = p.add_run(stripped)
            run.font.bold      = True
            run.font.size      = Pt(10.5)
            run.font.color.rgb = _COLOR_COMPANY
            continue

        # ------------------------------------------------------------------
        # Default body text (summary paragraphs, skill lines, etc.)
        # ------------------------------------------------------------------
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(stripped)
        run.font.size      = Pt(10)
        run.font.color.rgb = _COLOR_BODY

    # ------------------------------------------------------------------
    # Filename: {Company}_{JobTitle}_{YYYYMMDD}.docx
    # ------------------------------------------------------------------
    date_str      = datetime.now().strftime("%Y%m%d")
    company_clean = re.sub(r"[^\w]", "_", company or "Export").strip("_")
    job_clean     = re.sub(r"[^\w]", "_", job_title or "Resume").strip("_")
    filename      = f"{company_clean}_{job_clean}_{date_str}.docx"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read(), filename
