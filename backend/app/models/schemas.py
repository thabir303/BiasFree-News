"""
Pydantic models for request/response validation.
Ensures type safety and automatic API documentation.
"""
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
    message: str | None = Field(None, description="Additional message (e.g., verification info)")


class UserResponse(BaseModel):
    """User information response."""
    model_config = {"from_attributes": True}

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    category_preferences: list[str] | None = None


class CategoryPreferencesRequest(BaseModel):
    """Request model for updating category preferences."""
    categories: list[str] = Field(..., min_length=1, description="Ordered list of category keys by priority")


class CategoryPreferencesResponse(BaseModel):
    """Response model for category preferences."""
    categories: list[str] = Field(default_factory=list, description="Ordered category keys")
    message: str | None = None


class UpdateUsernameRequest(BaseModel):
    """Request to update username."""
    new_username: str = Field(..., min_length=3, max_length=50, description="New unique username")


class ForgotPasswordRequest(BaseModel):
    """Request to send password reset OTP."""
    email: EmailStr = Field(..., description="User email address")


class VerifyOtpRequest(BaseModel):
    """Request to verify OTP."""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class ResetPasswordRequest(BaseModel):
    """Request to reset password after OTP verification."""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")


# ============================================
# User Analysis Schemas
# ============================================

class UserAnalysisCreate(BaseModel):
    """Request model for saving a manual analysis."""
    title: str | None = Field(None, description="Article title")
    original_content: str = Field(..., min_length=10, description="Original article content")
    is_biased: bool | None = None
    bias_score: float | None = None
    bias_summary: str | None = None
    biased_terms: list | None = None
    confidence: float | None = None
    debiased_content: str | None = None
    changes_made: list | None = None
    total_changes: int | None = 0
    generated_headlines: list | None = None
    recommended_headline: str | None = None
    headline_reasoning: str | None = None
    processing_time: float | None = None


class UserAnalysisResponse(BaseModel):
    """Response model for a saved user analysis."""
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    title: str | None = None
    original_content: str
    is_biased: bool | None = None
    bias_score: float | None = None
    bias_summary: str | None = None
    biased_terms: list | None = None
    confidence: float | None = None
    debiased_content: str | None = None
    changes_made: list | None = None
    total_changes: int | None = 0
    generated_headlines: list | None = None
    recommended_headline: str | None = None
    headline_reasoning: str | None = None
    processing_time: float | None = None
    created_at: str


class UserAnalysesListResponse(BaseModel):
    """Response model for list of user analyses."""
    analyses: list[UserAnalysisResponse]
    total: int


# ============================================
# Article Processing Schemas
# ============================================

class ArticleInput(BaseModel):
    """Input model for article analysis."""
    content: str = Field(..., min_length=50, description="Article content in Bengali")
    title: str | None = Field(None, description="Original article title")
    
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
    position: int | None = Field(None, description="Character position in text")


class BiasAnalysisResponse(BaseModel):
    """Response model for bias analysis."""
    is_biased: bool = Field(..., description="Whether article contains bias")
    bias_score: float = Field(..., ge=0.0, le=100.0, description="Bias score (0-100)")
    biased_terms: list[BiasedTerm] = Field(default_factory=list, description="List of biased terms")
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
    changes: list[ContentChange] = Field(default_factory=list, description="List of changes made")
    total_changes: int = Field(..., description="Number of changes made")


class HeadlineResponse(BaseModel):
    """Response model for headline generation."""
    original_title: str | None = Field(None, description="Original headline")
    generated_headlines: list[str] = Field(..., min_length=1, description="Generated neutral headlines")
    recommended_headline: str = Field(..., description="Most recommended headline")
    reasoning: str = Field(..., description="Why this headline is recommended")


class ScrapeRequest(BaseModel):
    """Request model for article scraping."""
    source: str = Field(..., description="Newspaper source: prothom_alo, jugantor, daily_star, dhaka_tribune")
    start_date: date = Field(..., description="Start date for scraping")
    end_date: date = Field(..., description="End date for scraping")
    section_ids: list[str] | None = Field(None, description="Optional section IDs for Prothom Alo (e.g., ['22237', '17533,17535'])")
    
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
    published_date: str | None = None
    source: str
    category: str | None = None  # রাজনীতি, বিশ্ব, মতামত, বাংলাদেশ


class ScrapeResponse(BaseModel):
    """Response model for scraping results."""
    articles: list[ScrapedArticle] = Field(default_factory=list)
    total_count: int = Field(..., description="Total articles scraped")
    source: str = Field(..., description="Newspaper source")
    date_range: str = Field(..., description="Date range scraped")


class FullProcessResponse(BaseModel):
    """Response for complete bias-free processing."""
    analysis: BiasAnalysisResponse
    debiased: DebiasResponse
    headline: HeadlineResponse
    processing_time_seconds: float = Field(..., description="Total processing time")
