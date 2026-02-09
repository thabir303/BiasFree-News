"""
Pydantic models for request/response validation.
Ensures type safety and automatic API documentation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import date


# ============================================
# Authentication Schemas
# ============================================

class UserSignup(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")


class UserSignin(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserResponse"
    message: Optional[str] = Field(None, description="Additional message (e.g., verification info)")


class UserResponse(BaseModel):
    """User information response."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================
# Article Processing Schemas
# ============================================

class ArticleInput(BaseModel):
    """Input model for article analysis."""
    content: str = Field(..., min_length=50, description="Article content in Bengali")
    title: Optional[str] = Field(None, description="Original article title")
    
    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Ensure content doesn't exceed max length."""
        from app.config import settings
        if len(v) > settings.max_article_length:
            raise ValueError(f"Article exceeds maximum length of {settings.max_article_length} characters")
        return v.strip()


class BiasedTerm(BaseModel):
    """Represents a biased term found in the article."""
    term: str = Field(..., description="Biased word or phrase")
    reason: str = Field(..., description="Why this term is biased")
    neutral_alternative: str = Field(..., description="Neutral replacement suggestion")
    severity: str = Field(..., description="Bias severity: low, medium, high")
    position: Optional[int] = Field(None, description="Character position in text")


class BiasAnalysisResponse(BaseModel):
    """Response model for bias analysis."""
    is_biased: bool = Field(..., description="Whether article contains bias")
    bias_score: float = Field(..., ge=0.0, le=100.0, description="Bias score (0-100)")
    biased_terms: List[BiasedTerm] = Field(default_factory=list, description="List of biased terms")
    summary: str = Field(..., description="Brief analysis summary")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence (0-1)")


class ContentChange(BaseModel):
    """Represents a change made during debiasing."""
    original: str = Field(..., description="Original biased text")
    debiased: str = Field(..., description="Neutral replacement text")
    reason: str = Field(..., description="Reason for change")


class DebiasResponse(BaseModel):
    """Response model for debiased content."""
    original_content: str = Field(..., description="Original article content")
    debiased_content: str = Field(..., description="Debiased article content")
    changes: List[ContentChange] = Field(default_factory=list, description="List of changes made")
    total_changes: int = Field(..., description="Number of changes made")


class HeadlineResponse(BaseModel):
    """Response model for headline generation."""
    original_title: Optional[str] = Field(None, description="Original headline")
    generated_headlines: List[str] = Field(..., min_length=1, description="Generated neutral headlines")
    recommended_headline: str = Field(..., description="Most recommended headline")
    reasoning: str = Field(..., description="Why this headline is recommended")


class ScrapeRequest(BaseModel):
    """Request model for article scraping."""
    source: str = Field(..., description="Newspaper source: prothom_alo, jugantor, daily_star, dhaka_tribune")
    start_date: date = Field(..., description="Start date for scraping")
    end_date: date = Field(..., description="End date for scraping")
    section_ids: Optional[List[str]] = Field(None, description="Optional section IDs for Prothom Alo (e.g., ['22237', '17533,17535'])")
    
    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate newspaper source."""
        allowed_sources = ["prothom_alo", "jugantor", "daily_star", "dhaka_tribune", "samakal"]
        if v.lower() not in allowed_sources:
            raise ValueError(f"Source must be one of: {', '.join(allowed_sources)}")
        return v.lower()
    
    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class ScrapedArticle(BaseModel):
    """Model for a scraped article."""
    title: str
    content: str
    url: str
    published_date: Optional[str] = None
    source: str
    category: Optional[str] = None  # রাজনীতি, বিশ্ব, মতামত, বাংলাদেশ


class ScrapeResponse(BaseModel):
    """Response model for scraping results."""
    articles: List[ScrapedArticle] = Field(default_factory=list)
    total_count: int = Field(..., description="Total articles scraped")
    source: str = Field(..., description="Newspaper source")
    date_range: str = Field(..., description="Date range scraped")


class FullProcessResponse(BaseModel):
    """Response for complete bias-free processing."""
    analysis: BiasAnalysisResponse
    debiased: DebiasResponse
    headline: HeadlineResponse
    processing_time_seconds: float = Field(..., description="Total processing time")
