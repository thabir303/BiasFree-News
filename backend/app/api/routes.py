"""
API routes for BiasFree News.
All endpoints with request/response validation and error handling.
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.schemas import (
    ArticleInput,
    BiasAnalysisResponse,
    DebiasResponse,
    HeadlineResponse,
    ScrapeRequest,
    ScrapeResponse,
    FullProcessResponse
)
from app.services import BiasDetectorService, NewsScraper
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create API router
router = APIRouter(prefix="/api", tags=["bias-detection"])

# Initialize services (singleton pattern)
bias_detector = BiasDetectorService()
scraper = NewsScraper()


@router.post("/analyze", response_model=BiasAnalysisResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_article(request: Request, article: ArticleInput) -> BiasAnalysisResponse:
    """
    Analyze article for bias detection.
    
    - **content**: Article content in Bengali (min 50 chars)
    - **title**: Optional article title
    
    Returns bias analysis with identified biased terms.
    """
    try:
        logger.info(f"Analyzing article with {len(article.content)} characters")
        result = await bias_detector.analyze_bias(article.content, article.title)
        return result
    except Exception as e:
        logger.error(f"Analysis endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/debias", response_model=DebiasResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def debias_article(request: Request, article: ArticleInput) -> DebiasResponse:
    """
    Debias article content by replacing biased terms with neutral alternatives.
    
    - **content**: Article content in Bengali
    
    Returns debiased content with tracked changes.
    """
    try:
        logger.info(f"Debiasing article with {len(article.content)} characters")
        result = await bias_detector.debias_article(article.content)
        return result
    except Exception as e:
        logger.error(f"Debias endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debiasing failed: {str(e)}")


@router.post("/generate-headline", response_model=HeadlineResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def generate_headline(request: Request, article: ArticleInput) -> HeadlineResponse:
    """
    Generate neutral, factual headline for article.
    
    - **content**: Article content in Bengali
    - **title**: Original headline (for comparison)
    
    Returns multiple headline suggestions with reasoning.
    """
    try:
        logger.info("Generating neutral headline")
        result = await bias_detector.generate_neutral_headline(
            article.content,
            article.title
        )
        return result
    except Exception as e:
        logger.error(f"Headline generation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Headline generation failed: {str(e)}")


@router.post("/scrape", response_model=ScrapeResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def scrape_articles(request: Request, scrape_req: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape articles from Bengali newspapers within date range.
    
    - **source**: Newspaper source (prothom_alo, jugantor, samakal)
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    
    Returns scraped articles (limited to max configured amount).
    """
    try:
        logger.info(
            f"Scraping {scrape_req.source} from {scrape_req.start_date} to {scrape_req.end_date}"
        )
        
        articles = await scraper.scrape_articles(
            scrape_req.source,
            scrape_req.start_date,
            scrape_req.end_date
        )
        
        date_range = f"{scrape_req.start_date} to {scrape_req.end_date}"
        
        return ScrapeResponse(
            articles=articles,
            total_count=len(articles),
            source=scrape_req.source,
            date_range=date_range
        )
    except Exception as e:
        logger.error(f"Scrape endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.post("/full-process", response_model=FullProcessResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def full_process(request: Request, article: ArticleInput) -> FullProcessResponse:
    """
    Complete bias-free processing pipeline.
    Performs analysis, debiasing, and headline generation in one request.
    
    - **content**: Article content in Bengali
    - **title**: Original article title
    
    Returns comprehensive results with all processing steps.
    """
    try:
        logger.info("Starting full bias-free processing")
        result = await bias_detector.full_process(article.content, article.title)
        return result
    except Exception as e:
        logger.error(f"Full process endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full processing failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "model": settings.openai_model
    }
