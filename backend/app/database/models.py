"""
SQLAlchemy database models for storing articles and analysis results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Enum, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
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
    category_preferences = Column(JSON, nullable=True)  # Ordered list of category keys e.g. ["রাজনীতি", "বিশ্ব", ...]
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, verified={self.is_verified})>"


class Article(Base):
    """Model for storing scraped articles."""
    
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)  # prothom_alo, daily_star, etc.
    category = Column(String(50), nullable=True, index=True)  # রাজনীতি, বিশ্ব, মতামত, বাংলাদেশ
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
    
    # Clustering
    cluster_id = Column(Integer, ForeignKey("article_clusters.id"), nullable=True, index=True)
    embedding = Column(LargeBinary, nullable=True)  # numpy array stored as bytes
    cluster = relationship("ArticleCluster", back_populates="articles")
    
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


class ArticleCluster(Base):
    """Model for grouping similar articles about the same event."""
    
    __tablename__ = "article_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_label = Column(String(500), nullable=True)  # Auto-generated topic label from titles
    representative_title = Column(String(500), nullable=True)  # Title of most representative article
    article_count = Column(Integer, default=0)
    avg_similarity = Column(Float, nullable=True)  # Average pairwise cosine similarity
    sources = Column(JSON, nullable=True)  # List of unique newspaper sources in cluster
    category = Column(String(50), nullable=True, index=True)  # Dominant category
    
    # Unified article (Feature 2 - to be filled later)
    unified_content = Column(Text, nullable=True)
    unified_headline = Column(String(500), nullable=True)
    debiased_unified_content = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    articles = relationship("Article", back_populates="cluster", lazy="dynamic")
    
    def __repr__(self):
        return f"<ArticleCluster(id={self.id}, label={self.cluster_label[:50] if self.cluster_label else 'N/A'}, count={self.article_count})>"


class UserAnalysis(Base):
    """Model for storing per-user manual article analyses."""
    
    __tablename__ = "user_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    original_content = Column(Text, nullable=False)
    
    # Bias Analysis Results
    is_biased = Column(Boolean, nullable=True)
    bias_score = Column(Float, nullable=True)
    bias_summary = Column(Text, nullable=True)
    biased_terms = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Debiased Content
    debiased_content = Column(Text, nullable=True)
    changes_made = Column(JSON, nullable=True)
    total_changes = Column(Integer, default=0)
    
    # Generated Headlines
    generated_headlines = Column(JSON, nullable=True)
    recommended_headline = Column(String(500), nullable=True)
    headline_reasoning = Column(Text, nullable=True)
    
    # Processing
    processing_time = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<UserAnalysis(id={self.id}, user_id={self.user_id}, title={self.title[:30] if self.title else 'N/A'})>"
