"""
LLM-powered interview question generation service.
Uses Ollama to generate role-specific technical and behavioural questions
and evaluate candidate answers with structured feedback.
"""
import re
import os
import json
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------
QUESTION_PROMPT = """You are a senior technical interviewer. Given a job description and optional
resume text, generate a balanced interview question set and return ONLY a valid JSON object.

Return exactly this schema:
{
  "role": "<inferred job title>",
  "company": "<inferred company name or 'the company'>",
  "questions": [
    {
      "id": 1,
      "category": "Technical",
      "difficulty": "Medium",
      "question": "<full question text>",
      "hint": "<one-sentence hint for the candidate>",
      "ideal_keywords": ["keyword1", "keyword2"]
    }
  ]
}

Rules:
- Generate exactly 6 questions: 3 Technical, 2 Behavioural, 1 Situational.
- Difficulty should be one of: Easy, Medium, Hard.
- ideal_keywords: 3-5 specific concepts/terms a strong answer should include.
- Return ONLY the JSON object. No markdown fences, no explanation."""

# ---------------------------------------------------------------------------
# Answer evaluation
# ---------------------------------------------------------------------------
EVALUATE_PROMPT = """You are a senior interviewer evaluating a candidate's answer.
Return ONLY a valid JSON object with this exact schema:
{
  "score": <integer 0-100>,
  "rating": "<Excellent|Good|Fair|Needs Work>",
  "strengths": ["specific strength 1", "strength 2"],
  "improvements": ["specific improvement 1", "improvement 2"],
  "model_answer_snippet": "<2-3 sentence ideal answer snippet for reference>"
}

Rules:
- score: Honest 0-100 based on completeness, accuracy, and communication.
- rating: Excellent (≥80), Good (60-79), Fair (40-59), Needs Work (<40).
- strengths: 1-3 genuine positives about the answer.
- improvements: 1-3 specific, actionable suggestions.
- Return ONLY the JSON. No markdown, no explanation."""


def generate_questions(job_description: str, resume_text: str = "") -> dict:
    """Generate a set of interview questions for the given role."""
    try:
        return _llm_generate_questions(job_description, resume_text)
    except Exception as e:
        print(f"[interview] Question generation failed ({e}), using fallback.")
        return _fallback_questions()


def evaluate_answer(question: str, answer: str, ideal_keywords: list[str]) -> dict:
    """Evaluate a candidate's answer and return structured feedback."""
    try:
        return _llm_evaluate(question, answer, ideal_keywords)
    except Exception as e:
        print(f"[interview] Answer evaluation failed ({e}), using fallback.")
        return _fallback_evaluation(answer, ideal_keywords)


# ---------------------------------------------------------------------------
# Private LLM helpers
# ---------------------------------------------------------------------------

def _llm_generate_questions(job_description: str, resume_text: str) -> dict:
    jd_truncated = job_description[:2500] if len(job_description) > 2500 else job_description
    resume_truncated = resume_text[:2000] if len(resume_text) > 2000 else resume_text

    user_msg = f"JOB DESCRIPTION:\n{jd_truncated}"
    if resume_truncated:
        user_msg += f"\n\nCANDIDATE RESUME:\n{resume_truncated}"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": QUESTION_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "format": "json",
    }

    response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120.0)
    response.raise_for_status()

    content = response.json().get("message", {}).get("content", "")
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(content)
    return parsed


def _llm_evaluate(question: str, answer: str, ideal_keywords: list[str]) -> dict:
    user_msg = (
        f"QUESTION: {question}\n\n"
        f"CANDIDATE ANSWER: {answer}\n\n"
        f"IDEAL KEYWORDS TO LOOK FOR: {', '.join(ideal_keywords)}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": EVALUATE_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "format": "json",
    }

    response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=90.0)
    response.raise_for_status()

    content = response.json().get("message", {}).get("content", "")
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    return json.loads(content)


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _fallback_questions() -> dict:
    return {
        "role": "Software Engineer",
        "company": "the company",
        "questions": [
            {
                "id": 1,
                "category": "Technical",
                "difficulty": "Medium",
                "question": "Explain the difference between REST and GraphQL APIs. When would you choose one over the other?",
                "hint": "Think about over-fetching, under-fetching, and use-case flexibility.",
                "ideal_keywords": ["REST", "GraphQL", "over-fetching", "schema", "query"]
            },
            {
                "id": 2,
                "category": "Technical",
                "difficulty": "Hard",
                "question": "How would you design a distributed rate limiter that works across multiple server instances?",
                "hint": "Consider token bucket, Redis, and synchronisation strategies.",
                "ideal_keywords": ["Redis", "token bucket", "sliding window", "distributed", "atomic"]
            },
            {
                "id": 3,
                "category": "Technical",
                "difficulty": "Medium",
                "question": "Walk me through how you would optimise a slow SQL query. What tools and strategies would you use?",
                "hint": "Think about EXPLAIN, indexes, and query structure.",
                "ideal_keywords": ["EXPLAIN", "index", "JOIN", "N+1", "query plan"]
            },
            {
                "id": 4,
                "category": "Behavioural",
                "difficulty": "Easy",
                "question": "Tell me about a time you disagreed with a technical decision. How did you handle it?",
                "hint": "Use the STAR method: Situation, Task, Action, Result.",
                "ideal_keywords": ["STAR", "collaboration", "communication", "outcome", "data-driven"]
            },
            {
                "id": 5,
                "category": "Behavioural",
                "difficulty": "Medium",
                "question": "Describe a project where you had to balance technical debt against delivering new features. What was your approach?",
                "hint": "Think about prioritisation frameworks and stakeholder communication.",
                "ideal_keywords": ["trade-offs", "stakeholders", "roadmap", "refactoring", "velocity"]
            },
            {
                "id": 6,
                "category": "Situational",
                "difficulty": "Medium",
                "question": "Your team's production service goes down 30 minutes before a major product launch. What do you do?",
                "hint": "Focus on your incident response process and communication strategy.",
                "ideal_keywords": ["rollback", "on-call", "logs", "communication", "post-mortem"]
            },
        ]
    }


def _fallback_evaluation(answer: str, ideal_keywords: list[str]) -> dict:
    words = answer.lower().split()
    matched = [kw for kw in ideal_keywords if kw.lower() in answer.lower()]
    score = min(100, 30 + len(matched) * 12 + min(len(words), 80))
    if score >= 80:
        rating = "Excellent"
    elif score >= 60:
        rating = "Good"
    elif score >= 40:
        rating = "Fair"
    else:
        rating = "Needs Work"

    return {
        "score": score,
        "rating": rating,
        "strengths": ["Answered the question directly."],
        "improvements": [
            f"Try to include more of these key concepts: {', '.join(ideal_keywords[:3])}.",
            "Provide a concrete real-world example to strengthen your answer."
        ],
        "model_answer_snippet": "A strong answer would reference specific technical concepts with a concrete example from your experience."
    }
