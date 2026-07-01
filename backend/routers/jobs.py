from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from services.vector_db import add_jobs_to_vector_db, search_jobs, clear_vector_db
from services.scraper import scrape_all
import uuid

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["Jobs"]
)

# Seed data — realistic job listings for AI/ML roles
SEED_JOBS = [
    {
        "title": "Senior AI Engineer",
        "company": "OpenAI",
        "location": "San Francisco, CA (Hybrid)",
        "description_text": "We are looking for a Senior AI Engineer to build next-generation LLMs and inference systems. You will work on distributed training pipelines using PyTorch and Kubernetes, optimize transformer architectures for production deployment, and collaborate with researchers on novel NLP techniques. Requirements: 5+ years Python, deep expertise in PyTorch or TensorFlow, experience with distributed systems and GPU clusters, strong understanding of transformer architectures and attention mechanisms.",
        "url": "https://openai.com/careers",
        "salary_range": "$200k - $350k",
        "source": "Seed"
    },
    {
        "title": "Machine Learning Engineer",
        "company": "Google DeepMind",
        "location": "Mountain View, CA",
        "description_text": "Join the Google DeepMind team to optimize deep learning models for production at scale. You will design ML pipelines using TensorFlow and JAX, build MLOps infrastructure on GCP with Kubernetes, and develop evaluation frameworks for model quality. Requirements: Strong Python and C++ skills, TensorFlow or JAX experience, MLOps and CI/CD expertise, familiarity with Apache Spark and BigQuery for large-scale data processing.",
        "url": "https://careers.google.com",
        "salary_range": "$180k - $300k",
        "source": "Seed"
    },
    {
        "title": "Applied AI Scientist",
        "company": "Meta",
        "location": "Menlo Park, CA (Hybrid)",
        "description_text": "As an Applied AI Scientist at Meta, you will develop and deploy state-of-the-art NLP and computer vision models powering billions of user interactions. You will work on recommendation systems, content understanding, and generative AI features. Requirements: PhD or MS in CS/ML, expertise in PyTorch, experience with large-scale distributed training, deep knowledge of NLP including transformers, BERT, and GPT architectures.",
        "url": "https://metacareers.com",
        "salary_range": "$190k - $340k",
        "source": "Seed"
    },
    {
        "title": "Data Scientist — Recommendations",
        "company": "Spotify",
        "location": "Remote (US/EU)",
        "description_text": "Analyze massive datasets to improve Spotify's recommendation algorithms and personalization engine. You will build statistical models, run A/B tests at scale, and develop feature engineering pipelines. Requirements: Strong SQL and Python skills, experience with Pandas, Scikit-Learn, and statistical modeling, familiarity with Apache Spark and data warehouse technologies.",
        "url": "https://spotify.com/jobs",
        "salary_range": "$150k - $220k",
        "source": "Seed"
    },
    {
        "title": "GenAI Platform Engineer",
        "company": "Anthropic",
        "location": "San Francisco, CA",
        "description_text": "Build and scale the infrastructure powering Claude and Anthropic's generative AI products. You will design RAG pipelines, vector database integrations, and LLM serving infrastructure. Requirements: Expert-level Python, experience with LangChain or LlamaIndex, vector databases (Pinecone, ChromaDB, Weaviate), Docker and Kubernetes, AWS or GCP.",
        "url": "https://anthropic.com/careers",
        "salary_range": "$210k - $370k",
        "source": "Seed"
    },
    {
        "title": "NLP Engineer",
        "company": "Cohere",
        "location": "Toronto, Canada (Remote-friendly)",
        "description_text": "Design and implement production NLP systems including text classification, entity extraction, semantic search, and embeddings. You will work on transformer models, fine-tuning pipelines, and evaluation frameworks. Requirements: MS or PhD with NLP focus, strong Python and PyTorch skills, experience with Hugging Face, SpaCy, or NLTK.",
        "url": "https://cohere.com/careers",
        "salary_range": "$160k - $260k",
        "source": "Seed"
    },
]


@router.post("/ingest")
async def ingest_seed_jobs(db: Session = Depends(get_db)):
    """
    Seeds the database with realistic job listings. Skips if already seeded.
    """
    existing_count = db.query(models.Job).filter(models.Job.source == "Seed").count()
    if existing_count >= len(SEED_JOBS):
        return {"status": "skipped", "message": f"Already have {existing_count} seed jobs."}

    jobs_to_add = []
    for job_data in SEED_JOBS:
        job_with_id = {**job_data, "id": str(uuid.uuid4())}
        db_job = models.Job(**job_with_id)
        db.add(db_job)
        jobs_to_add.append(job_with_id)

    db.commit()

    vector_data = [
        {
            "id": job["id"],
            "description": job["description_text"],
            "metadata": {"title": job["title"], "company": job["company"]}
        }
        for job in jobs_to_add
    ]
    add_jobs_to_vector_db(vector_data)

    return {"status": "success", "message": f"Ingested {len(jobs_to_add)} seed jobs."}


@router.post("/scrape")
async def scrape_external_jobs(query: str = "AI Engineer", db: Session = Depends(get_db)):
    """
    Scrapes Google, LinkedIn, and Remotive for real job listings,
    deduplicates, and saves them to the DB + vector store.
    """
    scraped = await scrape_all(query, limit_per_source=20)

    if not scraped:
        return {"status": "empty", "message": "No jobs found from external sources.", "count": 0}

    # Deduplicate against existing jobs by title+company
    existing_jobs = db.query(models.Job.title, models.Job.company).all()
    existing_set = {(j.title.lower(), j.company.lower()) for j in existing_jobs}

    new_jobs = []
    for job in scraped:
        key = (job["title"].lower(), job["company"].lower())
        if key not in existing_set:
            db_job = models.Job(**job)
            db.add(db_job)
            new_jobs.append(job)
            existing_set.add(key)

    if new_jobs:
        db.commit()

        vector_data = [
            {
                "id": job["id"],
                "description": job["description_text"],
                "metadata": {"title": job["title"], "company": job["company"]}
            }
            for job in new_jobs
        ]
        add_jobs_to_vector_db(vector_data)

    return {
        "status": "success",
        "message": f"Scraped {len(scraped)} listings, ingested {len(new_jobs)} new jobs.",
        "count": len(new_jobs),
    }


@router.get("/search")
async def search_jobs_api(query: str = "", limit: int = 20, db: Session = Depends(get_db)):
    """
    Searches jobs via semantic vector search.
    """
    if not query:
        jobs = db.query(models.Job).limit(limit).all()
        return {"results": jobs}

    try:
        vector_results = search_jobs(query, n_results=limit)
        ids = vector_results["ids"][0] if vector_results["ids"] else []

        if not ids:
            return {"results": []}

        jobs = db.query(models.Job).filter(models.Job.id.in_(ids)).all()
        return {"results": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_all_jobs(db: Session = Depends(get_db)):
    """
    Clears all job listings from SQLite and the Chroma vector database.
    """
    try:
        # Delete all job rows in SQLite
        db.query(models.Job).delete()
        db.commit()
        
        # Clear Chroma collection
        clear_vector_db()
        
        return {"status": "success", "message": "Successfully cleared all jobs from the database and vector index."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear jobs: {str(e)}")
