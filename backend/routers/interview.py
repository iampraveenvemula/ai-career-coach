from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.interview import generate_questions, evaluate_answer

router = APIRouter(
    prefix="/api/v1/interview",
    tags=["Interview"]
)


class GenerateQuestionsRequest(BaseModel):
    job_description: str
    resume_text: Optional[str] = ""


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    ideal_keywords: Optional[List[str]] = []


@router.post("/generate-questions")
async def api_generate_questions(req: GenerateQuestionsRequest):
    """
    Generates a balanced set of interview questions (Technical, Behavioural, Situational)
    tailored to the provided job description and optional candidate resume.
    """
    try:
        result = generate_questions(req.job_description, req.resume_text or "")
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-answer")
async def api_evaluate_answer(req: EvaluateAnswerRequest):
    """
    Evaluates a candidate's answer to an interview question and returns
    a score, rating, strengths, and improvement suggestions.
    """
    try:
        result = evaluate_answer(req.question, req.answer, req.ideal_keywords or [])
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
