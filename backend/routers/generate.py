from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from services.tailoring import tailor_resume, generate_cover_letter
from services.resume_builder import build_tailored_resume_docx, _llm_rewrite, _llm_refine, generate_docx_bytes

router = APIRouter(
    prefix="/api/v1/generate",
    tags=["Generate"]
)

class TailorRequest(BaseModel):
    resume_text: str
    job_description: str

class CoverLetterRequest(BaseModel):
    resume_text: str
    job_description: str
    company: str
    role: str

class TailoredTextRequest(BaseModel):
    resume_text: str
    job_description: str
    job_title: str = ""
    company: str = ""

class RefineRequest(BaseModel):
    current_resume: str
    instruction: str

class TailoredDocxRequest(BaseModel):
    resume_text: str          # already-tailored resume text (from in-portal editor)
    candidate_name: str = ""
    job_title: str = ""
    company: str = ""


@router.post("/resume")
async def api_tailor_resume(req: TailorRequest):
    try:
        result = tailor_resume(req.resume_text, req.job_description)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cover-letter")
async def api_generate_cover_letter(req: CoverLetterRequest):
    try:
        result = generate_cover_letter(req.resume_text, req.job_description, req.company, req.role)
        return {"status": "success", "cover_letter": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_keywords_gap(resume_text: str, job_description: str) -> tuple[list[str], list[str]]:
    import re
    def tokenize(text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./_-]{2,}", text.lower())
        tokens = set(words)
        word_list = [w for w in words if len(w) > 3]
        for i in range(len(word_list) - 1):
            tokens.add(f"{word_list[i]} {word_list[i+1]}")
        return tokens

    jd_tokens   = tokenize(job_description)
    res_tokens  = tokenize(resume_text)

    STOP = {"the", "and", "for", "with", "this", "that", "will", "have",
            "are", "you", "your", "our", "their", "from", "not", "but",
            "has", "can", "all", "any", "also", "more", "such", "been"}
    jd_keywords = {t for t in jd_tokens if t not in STOP and len(t) > 3}

    matched = sorted(jd_keywords & res_tokens)
    missing = sorted(jd_keywords - res_tokens)
    return matched, missing


@router.post("/tailored-text")
async def api_generate_tailored_text(req: TailoredTextRequest):
    """
    Edits the resume in-place using the LLM for the target job and returns
    the updated text to be rendered interactively in the portal.
    """
    try:
        matched, missing = extract_keywords_gap(req.resume_text, req.job_description)
        tailored_text = await _llm_rewrite(
            req.resume_text,
            req.job_description,
            matched_keywords=matched[:15],
            missing_keywords=missing[:25]
        )
        return {"status": "success", "resume_text": tailored_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine-resume")
async def api_refine_resume(req: RefineRequest):
    """
    Applies the user's inline refinement instruction to the current resume text.
    """
    try:
        refined_text = await _llm_refine(req.current_resume, req.instruction)
        return {"status": "success", "resume_text": refined_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tailored-docx")
async def api_generate_tailored_docx(req: TailoredDocxRequest):
    """
    Takes the already-tailored resume text from the in-portal editor and
    renders it as a downloadable DOCX with a smart filename.
    Filename format: {Company}_{JobTitle}_{YYYYMMDD}.docx
    """
    try:
        docx_bytes, filename = generate_docx_bytes(
            tailored_text=req.resume_text,
            candidate_name=req.candidate_name,
            job_title=req.job_title,
            company=req.company,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"',
                     "X-Filename": filename},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
