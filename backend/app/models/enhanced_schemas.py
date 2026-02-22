"""
Pydantic models for request/response validation.
Ensures type safety and automatic API documentation.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import date


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
    """Response model for debiasing."""
    original_content: str = Field(..., description="Original biased content")
    debiased_content: str = Field(..., description="Neutral rewritten content")
    changes_made: list[ContentChange] = Field(default_factory=list, description="List of changes")
    total_changes: int = Field(0, description="Total number of changes")
    bias_reduction_score: float = Field(0.0, description="Bias reduction percentage (0-100)")


class HeadlineResponse(BaseModel):
    """Response model for headline generation."""
    original_headline: str = Field(..., description="Original biased headline")
    generated_headlines: list[str] = Field(default_factory=list, description="List of neutral headlines")
    recommended_headline: str = Field(..., description="Best neutral headline")
    confidence: float = Field(0.0, description="Generation confidence (0-1)")


class ScrapedArticle(BaseModel):
    """Model for scraped article data."""
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Article content")
    url: str = Field(..., description="Original URL")
    source: str = Field(..., description="Newspaper source")
    published_date: str | None = Field(None, description="Publication date")
    author: str | None = Field(None, description="Article author")
    category: str | None = Field(None, description="Article category")


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


# Enhanced batch processing models
class BatchBiasAnalysisResponse(BaseModel):
    """Response model for batch bias analysis of multiple articles."""
    articles: list[BiasAnalysisResponse] = Field(default_factory=list, description="Bias analysis results for each article")
    total_processed: int = Field(..., description="Total number of articles processed")
    format_used: str = Field("TOON", description="Data format used (TOON/JSON)")
    token_savings: float = Field(0.0, description="Percentage of tokens saved using TOON format")
    processing_time_seconds: float | None = Field(None, description="Total processing time")


class BatchArticleInput(BaseModel):
    """Input model for batch article processing."""
    articles: list[ArticleInput] = Field(..., min_items=1, max_items=20, description="List of articles to analyze (max 20)")
    use_toon_format: bool = Field(True, description="Whether to use TOON format for efficiency")
    
    @field_validator("articles")
    @classmethod
    def validate_article_count(cls, v: list[ArticleInput]) -> list[ArticleInput]:
        """Ensure article count is within limits."""
        if len(v) > 20:
            raise ValueError("Maximum 20 articles allowed per batch request")
        return v


class EnhancedProcessingStats(BaseModel):
    """Statistics for enhanced batch processing."""
    total_processed: int = Field(..., description="Total articles processed")
    successful: int = Field(..., description="Successfully processed articles")
    failed: int = Field(..., description="Failed articles")
    biased_found: int = Field(..., description="Articles with bias detected")
    total_changes: int = Field(..., description="Total debiasing changes made")
    batches_processed: int = Field(..., description="Number of batches processed")
    format_used: str = Field(..., description="Processing format used")
    token_savings_avg: float = Field(0.0, description="Average token savings percentage")
    processing_time_seconds: float | None = Field(None, description="Total processing time")