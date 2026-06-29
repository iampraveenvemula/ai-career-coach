"""
LLM-powered resume tailoring service.
Uses Ollama to produce tailored summaries, optimizations, and ATS scores.
"""
import re
import os
import json
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

TAILOR_PROMPT = """You are a professional resume coach. Given a resume and a job description,
produce tailored suggestions and return ONLY a valid JSON object.

Return exactly this schema:
{
  "tailored_summary": "<one or two sentence professional summary tailored for this specific role>",
  "optimizations": ["specific actionable improvement 1", "improvement 2", "improvement 3"],
  "ats_score_before": <integer 0-100 estimated ATS score before changes>,
  "ats_score_after": <integer 0-100 estimated ATS score after applying optimizations>,
  "matched_skills": ["skills present in both resume and JD"],
  "missing_skills": ["important JD skills absent from resume"]
}

Rules:
- tailored_summary: Rewrite the candidate's professional summary to align with the JD role.
- optimizations: 3-5 specific, actionable bullet points referencing actual gaps.
- ats_score_before / after: Realistic integers 0-100.
- matched_skills / missing_skills: Specific technical skills, tools, or keywords.
- Return ONLY the JSON object. No markdown fences, no explanation."""

COVER_LETTER_PROMPT = """You are an expert cover letter writer. Given a resume and job details,
write a professional, personalized cover letter.

Return ONLY the plain text of the cover letter. No JSON, no markdown, no explanation.
The letter should:
- Open with a strong, specific hook referencing the company and role.
- Highlight 2-3 specific skills/achievements from the resume that match the JD.
- Show genuine interest in the company's mission.
- Close with a clear call to action.
- Be concise (3-4 paragraphs, under 300 words)."""


def tailor_resume(resume_text: str, job_description: str) -> dict:
    """
    Uses the Ollama LLM to produce tailored resume suggestions,
    ATS score, and skill gap analysis.
    """
    try:
        return _llm_tailor(resume_text, job_description)
    except Exception as e:
        print(f"[tailoring] Ollama tailoring failed ({e}), using fallback.")
        return _fallback_tailor(resume_text, job_description)


def _llm_tailor(resume_text: str, job_description: str) -> dict:
    resume_truncated = resume_text[:4000] if len(resume_text) > 4000 else resume_text
    jd_truncated = job_description[:2000] if len(job_description) > 2000 else job_description

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": TAILOR_PROMPT},
            {"role": "user", "content": f"RESUME:\n{resume_truncated}\n\nJOB DESCRIPTION:\n{jd_truncated}"},
        ],
        "stream": False,
        "format": "json",
    }

    response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120.0)
    response.raise_for_status()

    content = response.json().get("message", {}).get("content", "")
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(content)

    return {
        "tailored_summary": parsed.get("tailored_summary", ""),
        "optimizations": parsed.get("optimizations", []),
        "ats_score_before": int(parsed.get("ats_score_before", 50)),
        "ats_score_after": int(parsed.get("ats_score_after", 70)),
        "matched_skills": parsed.get("matched_skills", []),
        "missing_skills": parsed.get("missing_skills", []),
    }


def _fallback_tailor(resume_text: str, job_description: str) -> dict:
    return {
        "tailored_summary": "Experienced professional seeking to contribute expertise to this role.",
        "optimizations": [
            "Add keywords from the job description to improve ATS matching.",
            "Quantify achievements with specific metrics.",
            "Tailor your summary to match the role requirements.",
        ],
        "ats_score_before": 50,
        "ats_score_after": 65,
        "matched_skills": [],
        "missing_skills": [],
    }


def generate_cover_letter(resume_text: str, job_description: str, company: str, role: str) -> str:
    """
    Uses the Ollama LLM to write a personalized cover letter.
    """
    try:
        return _llm_cover_letter(resume_text, job_description, company, role)
    except Exception as e:
        print(f"[tailoring] Cover letter LLM failed ({e}), using fallback.")
        return _fallback_cover_letter(company, role)


def _llm_cover_letter(resume_text: str, job_description: str, company: str, role: str) -> str:
    resume_truncated = resume_text[:3000] if len(resume_text) > 3000 else resume_text
    jd_truncated = job_description[:1500] if len(job_description) > 1500 else job_description

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": COVER_LETTER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Company: {company}\nRole: {role}\n\n"
                    f"RESUME:\n{resume_truncated}\n\n"
                    f"JOB DESCRIPTION:\n{jd_truncated}"
                ),
            },
        ],
        "stream": False,
    }

    response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120.0)
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "").strip()


def _fallback_cover_letter(company: str, role: str) -> str:
    return (
        f"Dear Hiring Manager at {company},\n\n"
        f"I am writing to express my strong interest in the {role} position. "
        f"My background and experience make me a strong candidate for this role, "
        f"and I am confident in my ability to contribute meaningfully to your team.\n\n"
        f"I welcome the opportunity to discuss how my experience can support your team's goals.\n\n"
        f"Best regards"
    )
