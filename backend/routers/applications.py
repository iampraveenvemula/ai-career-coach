from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import re

router = APIRouter(
    prefix="/api/v1",
    tags=["Applications"]
)

class ApplicationCreateRequest(BaseModel):
    job_id: str
    status: str
    ats_score: Optional[int] = None

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

@router.post("/applications")
async def track_application(req: ApplicationCreateRequest, db: Session = Depends(get_db)):
    user = get_default_user(db)
    
    # Check if job exists
    job = db.query(models.Job).filter(models.Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Check if application already exists
    app_entry = db.query(models.Application).filter(
        models.Application.user_id == user.id,
        models.Application.job_id == req.job_id
    ).first()
    
    # Validate status
    try:
        status_enum = models.ApplicationStatus[req.status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
        
    if app_entry:
        app_entry.status = status_enum
        if req.ats_score is not None:
            app_entry.ats_score = req.ats_score
        app_entry.applied_at = datetime.utcnow()
    else:
        app_entry = models.Application(
            user_id=user.id,
            job_id=req.job_id,
            status=status_enum,
            ats_score=req.ats_score
        )
        db.add(app_entry)
        
    db.commit()
    db.refresh(app_entry)
    
    return {"status": "success", "application_id": app_entry.id, "job_status": app_entry.status.value}

@router.get("/applications")
async def get_applications(db: Session = Depends(get_db)):
    user = get_default_user(db)
    apps = db.query(models.Application).filter(models.Application.user_id == user.id).all()
    
    results = []
    for app in apps:
        job = db.query(models.Job).filter(models.Job.id == app.job_id).first()
        results.append({
            "id": app.id,
            "job_id": app.job_id,
            "status": app.status.value,
            "ats_score": app.ats_score,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "job": {
                "title": job.title if job else "Unknown",
                "company": job.company if job else "Unknown",
                "location": job.location if job else "Unknown",
                "salary_range": job.salary_range if job else "Unknown"
            }
        })
    return {"results": results}

@router.get("/analytics/dashboard")
async def get_analytics_dashboard(db: Session = Depends(get_db)):
    user = get_default_user(db)
    apps = db.query(models.Application).filter(models.Application.user_id == user.id).all()
    
    # Summary calculations
    total_apps = len(apps)
    # Sent applications: not SAVED
    sent_apps = [a for a in apps if a.status != models.ApplicationStatus.SAVED]
    sent_count = len(sent_apps)
    
    # Avg ATS score
    ats_scores = [a.ats_score for a in apps if a.ats_score is not None]
    avg_ats = int(sum(ats_scores) / len(ats_scores)) if ats_scores else 0
    
    # Interviews scheduled
    interviews_count = len([a for a in apps if a.status == models.ApplicationStatus.INTERVIEWING])
    
    # Response rate: (Interviewing + Rejected + Offer) / Sent
    responded_apps = [a for a in sent_apps if a.status in {models.ApplicationStatus.INTERVIEWING, models.ApplicationStatus.REJECTED, models.ApplicationStatus.OFFER}]
    response_rate = int((len(responded_apps) / sent_count) * 100) if sent_count > 0 else 0
    
    # Pipeline breakdown
    status_counts = {
        "Offer": len([a for a in apps if a.status == models.ApplicationStatus.OFFER]),
        "Interviewing": interviews_count,
        "Applied": len([a for a in apps if a.status == models.ApplicationStatus.APPLIED]),
        "Saved": len([a for a in apps if a.status == models.ApplicationStatus.SAVED]),
        "Rejected": len([a for a in apps if a.status == models.ApplicationStatus.REJECTED]),
    }
    
    # Recent applications (latest 6)
    sorted_apps = sorted(apps, key=lambda a: a.applied_at or datetime.min, reverse=True)[:6]
    recent_list = []
    for app in sorted_apps:
        job = db.query(models.Job).filter(models.Job.id == app.job_id).first()
        days_ago = 0
        if app.applied_at:
            delta = datetime.utcnow() - app.applied_at
            days_ago = delta.days
            
        recent_list.append({
            "company": job.company if job else "Unknown",
            "role": job.title if job else "Unknown",
            "ats": app.ats_score or 0,
            "status": app.status.value.capitalize(),
            "daysAgo": max(0, days_ago)
        })

    # 1. ATS History — get last 4 applications that have an ATS score, sorted chronologically
    history_apps = db.query(models.Application).filter(
        models.Application.user_id == user.id,
        models.Application.ats_score.isnot(None)
    ).order_by(models.Application.applied_at.asc()).all()

    ats_history = []
    for i, app_entry in enumerate(history_apps[-4:]):
        ats_history.append({
            "week": f"App {i+1}",
            "score": app_entry.ats_score
        })
    
    # Fallback/baseline if no applications have a score yet
    if not ats_history:
        resume = db.query(models.Resume).filter(models.Resume.user_id == user.id).first()
        if resume:
            ats_history = [{"week": "Baseline", "score": 50}]
        else:
            ats_history = []

    # 2. Skill Gaps — dynamic analysis comparing resume parsed skills to target jobs
    skill_gaps = []
    resume = db.query(models.Resume).filter(models.Resume.user_id == user.id).first()
    candidate_skills = set(s.lower().strip() for s in (resume.parsed_skills or [])) if resume else set()

    # List of common industry keywords to scan for in the JDs
    TECH_KEYWORDS = {
        "python", "javascript", "typescript", "pytorch", "tensorflow", "jax", "kubernetes",
        "docker", "aws", "gcp", "azure", "sql", "nosql", "mongodb", "postgres", "redis",
        "kafka", "spark", "hadoop", "git", "linux", "graphql", "rest", "grpc", "microservices",
        "mlops", "ci/cd", "rust", "go", "java", "c++", "scala", "agile", "scrum", "system design"
    }

    job_ids = [a.job_id for a in apps]
    jobs_list = db.query(models.Job).filter(models.Job.id.in_(job_ids)).all() if job_ids else []

    jd_keyword_counts = {}
    for j in jobs_list:
        desc_lower = (j.description_text or "").lower()
        for kw in TECH_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower):
                jd_keyword_counts[kw] = jd_keyword_counts.get(kw, 0) + 1

    # Find keywords that appear in the target JDs but are NOT in candidate resume skills
    missing_counts = {}
    for kw, count in jd_keyword_counts.items():
        if kw not in candidate_skills:
            missing_counts[kw] = count

    # Get top 5 most frequently requested missing skills
    sorted_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    for kw, count in sorted_missing:
        # Generate a dynamic coverage score based on count (more appearances = bigger gap/lower coverage)
        # If candidate completely lacks it, we show coverage between 10% to 40% depending on appearance count
        coverage_pct = max(10, 50 - (count * 10))
        skill_gaps.append({
            "skill": kw.capitalize() if kw not in {"gcp", "aws", "sql", "mlops", "jax", "ci/cd"} else kw.upper(),
            "coverage": coverage_pct
        })
        
    return {
        "summary_stats": [
            {"id": "stat-applications", "label": "Applications Sent", "value": sent_count, "delta": f"+{sent_count} total", "positive": True},
            {"id": "stat-avg-ats", "label": "Average ATS Score", "value": f"{avg_ats}%", "delta": "+0% change", "positive": True},
            {"id": "stat-interviews", "label": "Interviews Scheduled", "value": interviews_count, "delta": "Active stages", "positive": True},
            {"id": "stat-response-rate", "label": "Response Rate", "value": f"{response_rate}%", "delta": "Response rate", "positive": True}
        ],
        "pipeline_breakdown": [
            {"status": "Offer", "count": status_counts["Offer"]},
            {"status": "Interviewing", "count": status_counts["Interviewing"]},
            {"status": "Applied", "count": status_counts["Applied"]},
            {"status": "Saved", "count": status_counts["Saved"]},
            {"status": "Rejected", "count": status_counts["Rejected"]}
        ],
        "recent_applications": recent_list,
        "ats_history": ats_history,
        "skill_gaps": skill_gaps
    }
