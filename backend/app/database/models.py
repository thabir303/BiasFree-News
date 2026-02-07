"""
SQLAlchemy database models for storing articles and analysis results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User roles enum."""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """Model for storing user accounts."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)  # Username is NOT unique
    email = Column(String(100), unique=True, nullable=False, index=True)  # Only email is unique
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, verified={self.is_verified})>"


class Article(Base):
    """Model for storing scraped articles."""
    
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)  # prothom_alo, daily_star, etc.
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(500), nullable=True)
    original_content = Column(Text, nullable=False)
    published_date = Column(DateTime, nullable=True, index=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Bias Analysis Results
    is_biased = Column(Boolean, nullable=True)
    bias_score = Column(Float, nullable=True)
    bias_summary = Column(Text, nullable=True)
    biased_terms = Column(JSON, nullable=True)  # List of biased terms with details
    
    # Debiased Content
    debiased_content = Column(Text, nullable=True)
    changes_made = Column(JSON, nullable=True)  # List of changes (original -> debiased)
    total_changes = Column(Integer, default=0)
    
    # Processing Status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Generated Headlines
    generated_headlines = Column(JSON, nullable=True)
    recommended_headline = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Article(id={self.id}, source={self.source}, title={self.title[:50] if self.title else 'N/A'})>"


class SchedulerLog(Base):
    """Model for logging scheduler runs."""
    
    __tablename__ = "scheduler_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, partial
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    articles_scraped = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SchedulerLog(id={self.id}, job={self.job_name}, status={self.status})>"
