from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.parser import extract_text_from_file, extract_skills_from_text
from services.analyzer import analyze_resume_with_llm
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
    Fast keyword-overlap ATS score — no LLM, responds in ~10ms.
    Used for live score updates in the Resume Studio after each inline refinement.
    Returns: { score: int, matched: list[str], missing: list[str] }
    """
    import re

    def tokenize(text: str) -> set[str]:
        # Extract meaningful tokens: words 3+ chars, preserve compound terms
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./_-]{2,}", text.lower())
        # Also extract 2-word phrases (bigrams)
        tokens = set(words)
        word_list = [w for w in words if len(w) > 3]
        for i in range(len(word_list) - 1):
            tokens.add(f"{word_list[i]} {word_list[i+1]}")
        return tokens

    jd_tokens   = tokenize(req.job_description)
    res_tokens  = tokenize(req.resume_text)

    # Weight tokens by frequency in JD (more frequent = more important)
    jd_word_count: dict[str, int] = {}
    for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#./_-]{2,}", req.job_description.lower()):
        jd_word_count[t] = jd_word_count.get(t, 0) + 1

    # Filter to meaningful JD tokens (remove ultra-common stop words)
    STOP = {"the", "and", "for", "with", "this", "that", "will", "have",
            "are", "you", "your", "our", "their", "from", "not", "but",
            "has", "can", "all", "any", "also", "more", "such", "been"}
    jd_keywords = {t for t in jd_tokens if t not in STOP and len(t) > 3}

    matched = sorted(jd_keywords & res_tokens)
    missing = sorted(jd_keywords - res_tokens)

    # Score: weighted by coverage, boosted for longer matches (phrases count more)
    if not jd_keywords:
        score = 50
    else:
        phrase_matches = sum(1 for m in matched if " " in m)
        word_matches   = sum(1 for m in matched if " " not in m)
        # Phrases worth 2x
        weighted_match = word_matches + phrase_matches * 2
        total_weighted = len([t for t in jd_keywords if " " not in t]) + \
                         len([t for t in jd_keywords if " " in t]) * 2
        score = min(100, int((weighted_match / max(total_weighted, 1)) * 100))

    return {
        "score": score,
        "matched": matched[:20],
        "missing": missing[:20],
    }
