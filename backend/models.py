from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text, DateTime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from database import Base
import uuid

class ApplicationStatus(enum.Enum):
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFER = "OFFER"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String)
    experience_years = Column(Integer, default=0)
    target_roles = Column(JSON)  # List of roles
    target_locations = Column(JSON) # List of locations
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="user")
    applications = relationship("Application", back_populates="user")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    original_file_url = Column(String)
    parsed_skills = Column(JSON)
    parsed_experience = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    applications = relationship("Application", back_populates="resume_used")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    description_text = Column(Text)
    url = Column(String)
    salary_range = Column(String)
    source = Column(String)
    posted_at = Column(DateTime)
    vector_id = Column(String)

    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    job_id = Column(String, ForeignKey("jobs.id"))
    resume_used_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SAVED)
    ats_score = Column(Integer, nullable=True)
    match_score = Column(Integer, nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    resume_used = relationship("Resume", back_populates="applications")
