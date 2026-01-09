"""
Enhanced API routes with database integration and scheduler control.
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Request, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.schemas import (
    ArticleInput,
    BiasAnalysisResponse,
    DebiasResponse,
    HeadlineResponse,
    FullProcessResponse
)
from app.database.database import get_db
from app.database.models import Article, SchedulerLog
from app.services.bias_detector import BiasDetectorService
from app.services.scheduler import get_scheduler
from app.services.article_processor import ArticleProcessor
from app.config import settings
from app.config.newspapers import get_all_newspaper_keys

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create API router
router = APIRouter(prefix="/api", tags=["bias-detection"])

# Initialize services
bias_detector = BiasDetectorService()


@router.post("/analyze", response_model=BiasAnalysisResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_article(request: Request, article: ArticleInput) -> BiasAnalysisResponse:
    """
    Analyze article for bias detection.
    
    - **content**: Article content (min 50 chars)
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
    Remove bias from article content and generate neutral version.
    
    - **content**: Biased article content
    - **title**: Optional original title
    
    Returns debiased content with change tracking.
    """
    try:
        logger.info(f"Debiasing article with {len(article.content)} characters")
        
        # First detect bias
        analysis = await bias_detector.analyze_bias(article.content, article.title)
        
        if not analysis.is_biased:
            return DebiasResponse(
                original_content=article.content,
                debiased_content=article.content,
                changes_made=[],
                total_changes=0,
                bias_reduction_score=0.0
            )
        
        # Convert biased terms to expected format
        biased_terms = [term.model_dump() for term in analysis.biased_terms]
        
        # Then debias
        result = await bias_detector.debias_article(article.content, biased_terms)
        return result
        
    except Exception as e:
        logger.error(f"Debias endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debiasing failed: {str(e)}")


@router.post("/full-process", response_model=FullProcessResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def full_process(request: Request, article: ArticleInput) -> FullProcessResponse:
    """
    Complete bias-free processing: analyze, debias, and generate headline.
    
    - **content**: Article content
    - **title**: Optional original title
    
    Returns complete processing results in one call.
    """
    try:
        logger.info(f"Full processing article with {len(article.content)} characters")
        
        start_time = datetime.now()
        result = await bias_detector.full_process(article.content, article.title)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return FullProcessResponse(
            analysis=result.analysis,
            debiased=result.debiased,
            headline=result.headline,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Full process endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full processing failed: {str(e)}")


@router.post("/scrape")
async def scrape_articles(
    background_tasks: BackgroundTasks,
    newspapers: Optional[List[str]] = Query(None, description="Specific newspapers to scrape"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    max_articles: int = Query(50, ge=1, le=500, description="Maximum articles per newspaper"),
    process_immediately: bool = Query(False, description="Process articles immediately after scraping"),
    db: Session = Depends(get_db)
):
    """
    Scrape articles from newspapers and optionally process them.
    
    - **newspapers**: Optional list of newspaper keys (scrapes all if empty)
    - **start_date**: Optional start date (defaults to today)
    - **end_date**: Optional end date (defaults to today)
    - **max_articles**: Maximum articles per newspaper (1-500)
    - **process_immediately**: Whether to process articles after scraping
    """
    try:
        from app.services.scraper import NewsScraper
        scraper = NewsScraper()
        
        # Set default dates if not provided
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.today()
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date")
        
        # Get newspaper keys
        if not newspapers:
            newspapers = get_all_newspaper_keys()
        else:
            # Validate provided newspapers
            valid_newspapers = get_all_newspaper_keys()
            invalid = [n for n in newspapers if n not in valid_newspapers]
            if invalid:
                raise HTTPException(status_code=400, detail=f"Invalid newspapers: {invalid}")
        
        logger.info(f"Starting scrape for {len(newspapers)} newspapers, dates: {start_date} to {end_date}")
        
        # Start scraping in background
        background_tasks.add_task(
            scraper.scrape_multiple_newspapers,
            newspapers=newspapers,
            start_date=start_date,
            end_date=end_date,
            max_articles_per_newspaper=max_articles,
            process_after_scraping=process_immediately
        )
        
        return {
            "status": "started",
            "message": f"Scraping started for {len(newspapers)} newspapers",
            "newspapers": newspapers,
            "date_range": f"{start_date} to {end_date}",
            "max_articles_per_newspaper": max_articles,
            "process_immediately": process_immediately
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scrape endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/articles")
async def get_articles(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    processed: Optional[bool] = Query(None, description="Filter by processing status"),
    biased: Optional[bool] = Query(None, description="Filter by bias status"),
    source: Optional[str] = Query(None, description="Filter by news source")
):
    """
    Get articles with filtering and pagination.
    
    - **skip**: Number of articles to skip
    - **limit**: Maximum articles to return (1-100)
    - **processed**: Filter by processing status
    - **biased**: Filter by bias detection result
    - **source**: Filter by news source
    """
    try:
        query = db.query(Article)
        
        # Apply filters
        if processed is not None:
            query = query.filter(Article.processed == processed)
        if biased is not None:
            query = query.filter(Article.is_biased == biased)
        if source:
            query = query.filter(Article.source == source)
        
        # Get total count
        total = query.count()
        
        # Get articles with pagination
        articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        result = []
        for article in articles:
            result.append({
                "id": article.id,
                "title": article.title,
                "content": article.original_content[:500] + "..." if len(article.original_content) > 500 else article.original_content,
                "source": article.source,
                "url": article.url,
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "author": article.author,
                "processed": article.processed,
                "is_biased": article.is_biased,
                "bias_score": article.bias_score,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None,
                "created_at": article.created_at.isoformat()
            })
        
        return {
            "articles": result,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get articles error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch articles: {str(e)}")


@router.get("/articles/{article_id}")
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific article.
    
    - **article_id**: Article ID
    """
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return {
            "id": article.id,
            "title": article.title,
            "content": article.original_content,
            "debiased_content": article.debiased_content,
            "source": article.source,
            "url": article.url,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "author": article.author,
            "category": article.category,
            "processed": article.processed,
            "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            "processing_error": article.processing_error,
            "is_biased": article.is_biased,
            "bias_score": article.bias_score,
            "bias_summary": article.bias_summary,
            "biased_terms": article.biased_terms,
            "changes_made": article.changes_made,
            "total_changes": article.total_changes,
            "generated_headlines": article.generated_headlines,
            "recommended_headline": article.recommended_headline,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat() if article.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get article error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {str(e)}")


@router.post("/articles/{article_id}/reprocess")
async def reprocess_article(article_id: int, db: Session = Depends(get_db)):
    """
    Reprocess a specific article (useful after fixing bugs).
    
    - **article_id**: Article ID to reprocess
    """
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Reset processing status
        article.processed = False
        article.debiased_content = None
        article.changes_made = None
        article.total_changes = 0
        db.commit()
        
        # Re-process the article
        processor = ArticleProcessor(db)
        result = await processor.process_article(article)
        
        return {
            "status": "success",
            "article_id": article_id,
            "biased": result["biased"],
            "changes_made": result["changes_made"],
            "message": f"Article reprocessed successfully. {result['changes_made']} changes made."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reprocess article error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess article: {str(e)}")


@router.post("/articles/reprocess-all-biased")
async def reprocess_all_biased_articles(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max articles to reprocess")
):
    """
    Re-process all biased articles that have 0 changes.
    Useful after fixing the debiasing logic.
    """
    try:
        # Find biased articles with no changes
        articles = db.query(Article).filter(
            Article.is_biased == True,
            (Article.total_changes == 0) | (Article.total_changes == None)
        ).limit(limit).all()
        
        if not articles:
            return {"status": "success", "message": "No articles need reprocessing", "count": 0}
        
        processor = ArticleProcessor(db)
        total_changes = 0
        processed_count = 0
        
        for article in articles:
            # Reset and reprocess
            article.processed = False
            article.debiased_content = None
            article.changes_made = None
            article.total_changes = 0
            db.commit()
            
            result = await processor.process_article(article)
            processed_count += 1
            total_changes += result.get("changes_made", 0)
        
        return {
            "status": "success",
            "processed_count": processed_count,
            "total_changes": total_changes,
            "message": f"Reprocessed {processed_count} articles with {total_changes} total changes"
        }
    
    except Exception as e:
        logger.error(f"Reprocess all biased error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess articles: {str(e)}")


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and recent job history."""
    try:
        scheduler = get_scheduler()
        
        # Get scheduler info
        jobs = []
        next_run = None
        if scheduler._is_running and scheduler.scheduler:
            for job in scheduler.scheduler.get_jobs():
                job_next_run = job.next_run_time.isoformat() if job.next_run_time else None
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job_next_run
                })
                # Set next_run to the earliest scheduled job
                if job_next_run and (next_run is None or job_next_run < next_run):
                    next_run = job_next_run
        
        return {
            "running": scheduler._is_running,
            "next_run": next_run,
            "jobs": jobs
        }
    
    except Exception as e:
        logger.error(f"Scheduler status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.get("/scheduler/logs")
async def get_scheduler_logs(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Get recent scheduler job logs."""
    try:
        logs = db.query(SchedulerLog).order_by(
            SchedulerLog.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "job_name": log.job_name,
                "status": log.status,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "articles_scraped": log.articles_scraped,
                "articles_processed": log.articles_processed,
                "errors": log.errors,
                "error_message": log.error_message
            })
        
        return {"logs": result}
    
    except Exception as e:
        logger.error(f"Get scheduler logs error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


@router.get("/newspapers")
async def get_newspapers():
    """Get list of configured newspapers."""
    try:
        from app.config.newspapers import NEWSPAPER_CONFIGS
        
        newspapers = []
        for key, config in NEWSPAPER_CONFIGS.items():
            newspapers.append({
                "key": config.key,
                "name": config.name,
                "base_url": config.base_url,
                "language": config.language,
                "enabled": config.enabled
            })
        
        return {"newspapers": newspapers}
    
    except Exception as e:
        logger.error(f"Get newspapers error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch newspapers: {str(e)}")


@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get overall statistics about scraped and processed articles."""
    try:
        total_articles = db.query(Article).count()
        processed_articles = db.query(Article).filter(Article.processed == True).count()
        biased_articles = db.query(Article).filter(Article.is_biased == True).count()
        
        # Count by source
        by_source = {}
        sources = db.query(Article.source).distinct().all()
        for (source,) in sources:
            count = db.query(Article).filter(Article.source == source).count()
            by_source[source] = count
        
        return {
            "total_articles": total_articles,
            "processed_articles": processed_articles,
            "processed_count": processed_articles,  # Frontend expects this
            "biased_articles": biased_articles,
            "biased_count": biased_articles,  # Frontend expects this
            "unprocessed_articles": total_articles - processed_articles,
            "by_source": by_source
        }
    
    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


# Enhanced batch processing routes with TOON format optimization
from app.models.enhanced_schemas import (
    BatchArticleInput,
    BatchBiasAnalysisResponse,
    EnhancedProcessingStats
)
from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
from app.services.enhanced_article_processor import EnhancedArticleProcessor


@router.post("/enhanced/analyze-batch", response_model=BatchBiasAnalysisResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_articles_batch(
    request: BatchArticleInput,
    db: Session = Depends(get_db)
) -> BatchBiasAnalysisResponse:
    """
    Analyze multiple articles for bias in a single LLM call with TOON format optimization.
    
    Features:
    - Processes up to 20 articles per request
    - Uses TOON format for 30-60% token reduction
    - Single LLM call for entire batch
    - Optimized for cost-effectiveness
    
    Args:
        request: Batch article input with up to 20 articles
        db: Database session
        
    Returns:
        Batch bias analysis response with results for all articles
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(f"Received batch analysis request for {len(request.articles)} articles")
        
        # Initialize enhanced bias detector
        enhanced_detector = EnhancedBiasDetectorService()
        
        # Convert input articles to format suitable for analysis
        articles_data = []
        for idx, article in enumerate(request.articles):
            articles_data.append({
                "id": f"article_{idx}",  # Generate unique ID
                "title": article.title or "Untitled",
                "content": article.content,
                "source": "user_input"
            })
        
        # Perform batch bias analysis
        result = await enhanced_detector.analyze_bias_batch(
            articles=articles_data,
            use_toon_format=request.use_toon_format
        )
        
        logger.info(
            f"Batch analysis complete: {result.total_processed} articles, "
            f"format: {result.format_used}, token savings: {result.token_savings}%"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.post("/enhanced/process-scraped-batch", response_model=EnhancedProcessingStats)
async def process_scraped_articles_batch(
    max_articles: int = Query(20, ge=1, le=100, description="Maximum articles to process"),
    use_enhanced: bool = Query(True, description="Use enhanced TOON-based processing"),
    db: Session = Depends(get_db)
) -> EnhancedProcessingStats:
    """
    Process scraped articles from database in optimized batches with TOON format.
    
    Features:
    - Processes up to 20 articles per LLM call
    - Uses TOON format for token efficiency (30-60% reduction)
    - Batch processing for cost optimization
    - Automatic fallback to individual processing
    - Maximum 20 articles per batch for LLM analysis
    
    Args:
        max_articles: Maximum number of articles to process (1-100)
        use_enhanced: Whether to use enhanced TOON-based processing
        db: Database session
        
    Returns:
        Processing statistics with batch metrics and token savings
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(f"Processing scraped articles: max={max_articles}, enhanced={use_enhanced}")
        
        # Initialize enhanced processor
        processor = EnhancedArticleProcessor(db)
        
        # Process articles with batch optimization
        stats = await processor.process_unprocessed_articles(limit=max_articles)
        
        logger.info(
            f"Scraped articles processing complete: "
            f"{stats['total_processed']} processed, "
            f"{stats['successful']} successful, "
            f"{stats['biased_found']} biased found"
        )
        
        # Convert stats to response model
        return EnhancedProcessingStats(
            total_processed=stats["total_processed"],
            successful=stats["successful"],
            failed=stats["failed"],
            biased_found=stats["biased_found"],
            total_changes=stats["total_changes"],
            batches_processed=stats.get("batches_processed", 0),
            format_used=stats["format_used"],
            token_savings_avg=stats.get("token_savings_avg", 0),
            processing_time_seconds=stats.get("processing_time_seconds")
        )
        
    except Exception as e:
        logger.error(f"Scraped articles processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/enhanced/toon-demo")
async def toon_format_demo() -> dict[str, Any]:
    """
    Demonstrate TOON format efficiency compared to JSON for article data.
    
    Returns:
        Comparison showing token savings achieved by TOON format
        with sample article data
    """
    try:
        from app.utils.enhanced_toon_formatter import enhanced_toon_formatter
        
        # Sample article data for demonstration
        sample_articles = [
            {
                "id": "1",
                "title": "রাজনৈতিক দলের নেতা বলেছেন",
                "content": "আজকের রাজনৈতিক পরিস্থিতি খুবই উত্তপ্ত। বিরোধী দলগুলো সরকারের বিরুদ্ধে কঠোর অবস্থান নিয়েছে।",
                "source": "prothom_alo",
                "date": "2024-01-09"
            },
            {
                "id": "2", 
                "title": "অর্থনৈতিক প্রবৃদ্ধির খবর",
                "content": "দেশের অর্থনীতি দ্রুত উন্নতি করছে। বিশেষজ্ঞরা বলছেন এই প্রবৃদ্ধি টেকসই হবে।",
                "source": "jugantor",
                "date": "2024-01-09"
            }
        ]
        
        # Convert to TOON format
        toon_output = enhanced_toon_formatter.format_article_batch_tabular(sample_articles, max_articles=2)
        
        # Calculate token savings
        import json
        original_json = json.dumps({"articles": sample_articles}, separators=(',', ':'))
        savings = enhanced_toon_formatter.calculate_token_savings({"articles": sample_articles}, toon_output)
        
        return {
            "json_format": original_json,
            "toon_format": toon_output,
            "token_savings": savings,
            "efficiency_improvement": f"{savings['savings_percent']}% fewer tokens",
            "description": "TOON format reduces token usage by declaring keys once and streaming values as rows",
            "benefits": [
                "30-60% reduction in token usage",
                "More efficient LLM processing",
                "Lower API costs",
                "Faster response times",
                "Better for batch processing"
            ]
        }
        
    except Exception as e:
        logger.error(f"TOON demo failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TOON demo failed: {str(e)}")


@router.get("/enhanced/stats")
async def get_enhanced_processing_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get enhanced processing statistics including TOON format usage and token savings.
    
    Args:
        db: Database session
        
    Returns:
        Processing statistics with enhanced metrics
        
    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        from app.database.models import Article
        
        # Get basic article statistics
        total_articles = db.query(Article).count()
        processed_articles = db.query(Article).filter(Article.processed == True).count()
        unprocessed_articles = db.query(Article).filter(Article.processed == False).count()
        biased_articles = db.query(Article).filter(Article.is_biased == True).count()
        
        # Get recent processing errors
        recent_errors = db.query(Article).filter(
            Article.processing_error.isnot(None)
        ).order_by(Article.processed_at.desc()).limit(5).all()
        
        error_summary = []
        for article in recent_errors:
            error_summary.append({
                "article_id": article.id,
                "title": article.title,
                "error": article.processing_error,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None
            })
        
        return {
            "total_articles": total_articles,
            "processed_articles": processed_articles,
            "unprocessed_articles": unprocessed_articles,
            "biased_articles": biased_articles,
            "processing_rate": round((processed_articles / total_articles * 100) if total_articles > 0 else 0, 2),
            "bias_detection_rate": round((biased_articles / processed_articles * 100) if processed_articles > 0 else 0, 2),
            "recent_errors": error_summary,
            "system_status": "operational",
            "enhanced_features": {
                "toon_format": True,
                "batch_processing": True,
                "max_articles_per_batch": 20,
                "token_reduction": "30-60%",
                "cost_optimization": "Significant API cost reduction",
                "llm_efficiency": "Improved response times"
            },
            "usage_recommendations": [
                "Use TOON format for batch processing (30-60% token savings)",
                "Process articles in batches of 20 for optimal efficiency",
                "Monitor token savings in processing statistics",
                "Use enhanced endpoints for cost-effective processing"
            ]
        }
        
    except Exception as e:
        logger.error(f"Enhanced stats retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")