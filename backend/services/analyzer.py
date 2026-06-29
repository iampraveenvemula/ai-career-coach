"""
LLM-powered resume analyzer.
Uses Ollama to score a resume against a job description and produce
ATS score, matched/missing skills, and actionable recommendations.
"""
import json
import re
import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

ANALYZE_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst and career coach.
Given a resume and a job description, analyze the match and return ONLY a valid JSON object.

Return exactly this schema:
{
  "ats_score": <integer 0-100 representing how well the resume matches the job description>,
  "matched_keywords": ["list", "of", "skills/keywords", "found", "in", "both"],
  "missing_keywords": ["list", "of", "important", "skills/keywords", "from", "JD", "missing", "in", "resume"],
  "recommendations": ["list", "of", "specific", "actionable", "suggestions", "to", "improve", "the", "resume"]
}

Rules:
- ats_score: Integer 0–100. Be realistic and precise. 70+ means good alignment.
- matched_keywords: Specific skills, tools, frameworks, or keywords appearing in both documents.
- missing_keywords: Important requirements from the JD not mentioned in the resume. List up to 10.
- recommendations: 3–5 specific, actionable suggestions to improve the resume for this role.
  Be specific — reference actual gaps, not generic advice.
- Return ONLY the JSON object. No markdown, no explanation."""


async def analyze_resume_with_llm(resume_text: str, job_description: str) -> dict:
    """
    Uses Ollama LLM to intelligently analyze a resume against a job description.
    Returns ATS score, matched/missing keywords, and recommendations.
    Falls back to a basic approach if Ollama is unavailable.
    """
    try:
        return await _llm_analyze(resume_text, job_description)
    except Exception as e:
        print(f"[analyzer] Ollama analysis failed ({e}), using fallback.")
        return _fallback_analyze(resume_text, job_description)


async def _llm_analyze(resume_text: str, job_description: str) -> dict:
    """Send resume + JD to Ollama and parse the structured analysis."""
    # Truncate to avoid context overflow
    resume_truncated = resume_text[:4000] if len(resume_text) > 4000 else resume_text
    jd_truncated = job_description[:2000] if len(job_description) > 2000 else job_description

    user_message = (
        f"RESUME:\n{resume_truncated}\n\n"
        f"JOB DESCRIPTION:\n{jd_truncated}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": ANALYZE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()

    data = response.json()
    content = data.get("message", {}).get("content", "")

    # Strip any accidental markdown fences
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

    parsed = json.loads(content)

    # Normalise types
    ats_score = int(parsed.get("ats_score", 50))
    matched = parsed.get("matched_keywords", [])
    missing = parsed.get("missing_keywords", [])
    recommendations = parsed.get("recommendations", [])

    if isinstance(matched, str):
        matched = [s.strip() for s in matched.split(",") if s.strip()]
    if isinstance(missing, str):
        missing = [s.strip() for s in missing.split(",") if s.strip()]
    if isinstance(recommendations, str):
        recommendations = [recommendations]

    return {
        "ats_score": max(0, min(100, ats_score)),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": recommendations,
    }


def _fallback_analyze(resume_text: str, job_description: str) -> dict:
    """Basic keyword overlap fallback when Ollama is unavailable."""
    COMMON = [
        "Python", "Java", "JavaScript", "SQL", "React", "Node.js", "AWS",
        "Docker", "Kubernetes", "Machine Learning", "Deep Learning", "Git",
        "FastAPI", "Django", "Flask", "TensorFlow", "PyTorch", "NLP", "CI/CD",
    ]
    resume_lower = resume_text.lower()
    jd_lower = job_description.lower()

    matched = [s for s in COMMON if s.lower() in resume_lower and s.lower() in jd_lower]
    missing = [s for s in COMMON if s.lower() in jd_lower and s.lower() not in resume_lower]

    ats_score = int(len(matched) / max(len(matched) + len(missing), 1) * 100)

    return {
        "ats_score": ats_score,
        "matched_keywords": matched,
        "missing_keywords": missing[:10],
        "recommendations": [
            "Add missing keywords from the job description to your resume.",
            "Quantify achievements with metrics where possible.",
            "Ensure your resume is tailored specifically to this role.",
        ],
    }
