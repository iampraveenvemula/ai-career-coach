from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Career Coach API",
    description="API for the AI Career Coach platform",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import resume, jobs, generate, ollama, interview, applications

app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(generate.router)
app.include_router(ollama.router)
app.include_router(interview.router)
app.include_router(applications.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Service is healthy"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Career Coach API"}
