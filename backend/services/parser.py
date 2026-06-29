import io
import json
import os
import re
import httpx
from pdfminer.high_level import extract_text
# pyrefly: ignore [missing-import]
from docx import Document

# ---------------------------------------------------------------------------
# File extraction helpers (unchanged)
# ---------------------------------------------------------------------------

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extracts raw text from a PDF, DOCX, or TXT file."""
    ext = filename.split(".")[-1].lower()
    if ext == "pdf":
        return _extract_from_pdf(file_bytes)
    elif ext in ["docx", "doc"]:
        return _extract_from_docx(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8")
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def _extract_from_pdf(file_bytes: bytes) -> str:
    return extract_text(io.BytesIO(file_bytes)).strip()


def _extract_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs]).strip()


# ---------------------------------------------------------------------------
# LLM-powered resume analysis
# ---------------------------------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are an expert resume parser. When given resume text, you extract
structured information and return ONLY a valid JSON object — no markdown, no explanation,
no extra text.

Return exactly this JSON schema:
{
  "skills": ["list", "of", "technical", "and", "soft", "skills"],
  "years_experience": <integer number of total years of professional experience, or 0 if unknown>,
  "education": "<highest degree and field, e.g. 'M.S. Computer Science, Stanford University'>",
  "summary": "<one sentence professional summary inferred from the resume>"
}

Rules:
- skills: Extract ALL technical skills, tools, frameworks, languages, and notable soft skills.
  Return up to 25 skills as an array of strings.
- years_experience: Calculate total years of professional work experience by reading job dates.
  If dates span e.g. 2018–2025, that is 7 years. Return an integer. Return 0 if truly unknown.
- education: Return the highest degree found, including field and institution if present.
  If none found, return "Not specified".
- summary: Write a concise one-sentence professional summary from the resume content.
- Return ONLY the JSON object. No markdown code fences, no explanation."""


def extract_skills_from_text(text: str) -> dict:
    """
    Uses a locally-running Ollama LLM to intelligently extract skills,
    years of experience, education, and a summary from resume text.

    Falls back to a basic extraction if Ollama is unavailable.
    """
    try:
        return _llm_extract(text)
    except Exception as e:
        print(f"[parser] Ollama extraction failed ({e}), falling back to basic extraction.")
        return _fallback_extract(text)


def _llm_extract(text: str) -> dict:
    """Send resume text to Ollama and parse the structured JSON response."""
    # Truncate very long resumes to avoid context window issues
    truncated = text[:6000] if len(text) > 6000 else text

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the resume text:\n\n{truncated}"},
        ],
        "stream": False,
        "format": "json",
    }

    response = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()

    data = response.json()
    # Ollama wraps the response in message.content
    content = data.get("message", {}).get("content", "")

    # Strip any accidental markdown fences
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

    parsed = json.loads(content)

    # Normalise types
    skills = parsed.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    years = parsed.get("years_experience", 0)
    if isinstance(years, str):
        # Extract first number found
        m = re.search(r"\d+", years)
        years = int(m.group()) if m else 0

    return {
        "skills": skills[:25],
        "years_experience": int(years) if years else 0,
        "education": parsed.get("education", "Not specified"),
        "summary": parsed.get("summary", ""),
    }


# ---------------------------------------------------------------------------
# Minimal fallback (used only when Ollama is completely unreachable)
# ---------------------------------------------------------------------------

def _fallback_extract(text: str) -> dict:
    """Very basic keyword extraction used only when Ollama is unavailable."""
    COMMON_SKILLS = [
        "Python", "Java", "JavaScript", "TypeScript", "SQL", "React", "Node.js",
        "FastAPI", "Django", "Flask", "AWS", "Docker", "Kubernetes", "TensorFlow",
        "PyTorch", "Machine Learning", "Deep Learning", "NLP", "Git", "Linux",
    ]
    found = [s for s in COMMON_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', text, re.IGNORECASE)]

    years = 0
    m = re.search(r'(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)', text, re.IGNORECASE)
    if m:
        years = int(m.group(1))

    edu = "Not specified"
    for deg in ["Ph.D", "Doctor", "Master", "M.S.", "M.Sc", "MBA", "Bachelor", "B.S.", "B.Tech"]:
        if deg.lower() in text.lower():
            edu = deg
            break

    return {
        "skills": found[:20],
        "years_experience": years,
        "education": edu,
        "summary": "",
    }
