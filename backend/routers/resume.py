from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.parser import extract_text_from_file, extract_skills_from_text
from services.analyzer import analyze_resume_with_llm
from services.ats_scorer import calculate_industry_score
from database import get_db
import models

router = APIRouter(
    prefix="/api/v1/resume",
    tags=["Resume"]
)

def get_default_user(db: Session):
    user = db.query(models.User).filter(models.User.id == "default-user").first()
    if not user:
        user = models.User(
            id="default-user",
            email="user@example.com",
            name="Default User",
            experience_years=3,
            target_roles=["Software Engineer"],
            target_locations=["Remote"]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/parse")
async def parse_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a resume file (PDF/DOCX/TXT) and use an LLM to extract
    skills, experience, education and a professional summary.
    Saves the parsed resume to the database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        contents = await file.read()
        extracted_text = extract_text_from_file(contents, file.filename)
        parsed_data = extract_skills_from_text(extracted_text)

        user = get_default_user(db)
        
        # Delete any existing resumes for default-user to keep it 1-to-1
        db.query(models.Resume).filter(models.Resume.user_id == user.id).delete()
        
        db_resume = models.Resume(
            user_id=user.id,
            original_file_url=file.filename,
            raw_text=extracted_text,
            parsed_skills=parsed_data.get("skills", []),
            parsed_experience={
                "education": parsed_data.get("education", "Not specified"),
                "summary": parsed_data.get("summary", ""),
                "years_experience": parsed_data.get("years_experience", 0)
            }
        )
        db.add(db_resume)
        db.commit()

        return {
            "status": "success",
            "filename": file.filename,
            "parsed_data": parsed_data,
            "raw_text": extracted_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str

@router.post("/analyze")
async def analyze_resume(req: AnalyzeRequest):
    """
    Score a resume against a job description using the LLM.
    Returns ATS score, matched/missing keywords, and recommendations.
    """
    try:
        result = await analyze_resume_with_llm(req.resume_text, req.job_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing resume: {str(e)}")


@router.post("/quick-score")
async def quick_score(req: AnalyzeRequest):
    """
    Industry-grade keyword-overlap and semantic ATS score.
    Used for live score updates in the Resume Studio.
    Returns: { score: int, matched: list[str], missing: list[str] }
    """
    try:
        # Note: If target title is not provided in req, we default to empty.
        res = calculate_industry_score(req.resume_text, req.job_description)
        return {
            "score": res["score"],
            "matched": res["matched"],
            "missing": res["missing"],
            "breakdown": res["breakdown"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
