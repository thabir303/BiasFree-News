"""
Enhanced API routes with database integration and scheduler control.
"""
import logging
import asyncio
from typing import List, Optional
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
    Debias article content by replacing biased terms with neutral alternatives.
    
    Returns debiased content with word-level change tracking.
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


@router.post("/full-process", response_model=FullProcessResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def full_process(request: Request, article: ArticleInput) -> FullProcessResponse:
    """
    Complete processing: analyze, debias, and generate headline.
    """
    try:
        logger.info("Running full processing pipeline")
        result = await bias_detector.full_process(article.content, article.title)
        return result
    except Exception as e:
        logger.error(f"Full process endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full processing failed: {str(e)}")


# ==================== NEW ENDPOINTS ====================

# Store active scraping jobs status
scraping_jobs = {}


async def run_scraping_task(
    job_id: str, 
    sources: List[str], 
    start_dt: datetime, 
    end_dt: datetime,
    section_ids: Optional[dict] = None
):
    """
    Background task to run scraping.
    
    Args:
        job_id: Unique job identifier
        sources: List of newspaper sources
        start_dt: Start datetime
        end_dt: End datetime
        section_ids: Optional dict mapping source to list of section IDs
    """
    try:
        scraping_jobs[job_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "sources": sources,
            "section_ids": section_ids,
            "progress": "Scraping in progress..."
        }
        
        scheduler = get_scheduler()
        stats = await scheduler.run_manual_scraping(sources, start_dt, end_dt, section_ids)
        
        scraping_jobs[job_id] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "statistics": stats
        }
        logger.info(f"Scraping job {job_id} completed: {stats}")
        
    except Exception as e:
        logger.error(f"Scraping job {job_id} failed: {str(e)}", exc_info=True)
        scraping_jobs[job_id] = {
            "status": "failed",
            "error": str(e)
        }


@router.post("/scrape/manual")
async def manual_scrape(
    request: Request,
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(default=None, alias="sources[]"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    prothom_alo_sections: Optional[List[str]] = Query(default=None, alias="prothom_alo_sections[]", description="Section IDs for Prothom Alo")
):
    """
    Manually trigger scraping for specific newspapers and date range.
    
    - **sources[]**: List of newspaper keys (prothom_alo, daily_star, jugantor, dhaka_tribune, samakal)
    - **start_date**: Start date for scraping (YYYY-MM-DD)
    - **end_date**: End date for scraping (YYYY-MM-DD)
    - **prothom_alo_sections[]**: Optional section IDs for Prothom Alo filtering
    
    Section IDs for Prothom Alo:
    - 22237: সর্বশেষ (Latest)
    - 17533,17535,17536,17538,22321,22236: রাজনীতি (Politics)
    - 17690,17693,17691,22329,22327,22330,17694: বাংলাদেশ (Bangladesh)
    - 17552,17553,22324,22325,22326,26653,17556,17555,23382,23383,17560: বিশ্ব (International)
    - 17562,22333,22334,22335,35622,17563,35623: খেলা (Sports)
    - 17736,17737,17739,23426,35867,35868: বিনোদন (Entertainment)
    
    If not provided, scrapes all enabled newspapers for today.
    Returns immediately and runs scraping in background.
    """
    try:
        # Log received parameters
        logger.info(f"Manual scraping API called:")
        logger.info(f"  - sources (raw): {sources}")
        logger.info(f"  - start_date: {start_date}")
        logger.info(f"  - end_date: {end_date}")
        logger.info(f"  - prothom_alo_sections: {prothom_alo_sections}")
        
        # Also try to get sources without [] if the alias doesn't work
        if not sources:
            query_params = dict(request.query_params)
            logger.info(f"  - Query params: {query_params}")
            if 'sources[]' in query_params:
                sources_raw = request.query_params.getlist('sources[]')
                sources = sources_raw if sources_raw else None
                logger.info(f"  - Found sources[] in query: {sources}")
        
        # Try to get prothom_alo_sections if not already retrieved
        if not prothom_alo_sections:
            query_params = dict(request.query_params)
            if 'prothom_alo_sections[]' in query_params:
                prothom_alo_sections = request.query_params.getlist('prothom_alo_sections[]')
                logger.info(f"  - Found prothom_alo_sections[] in query: {prothom_alo_sections}")
        
        # Validate sources
        if sources:
            valid_sources = get_all_newspaper_keys()
            invalid = [s for s in sources if s not in valid_sources]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid sources: {invalid}. Valid: {valid_sources}"
                )
        
        # Convert dates to datetime
        start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        # Prepare section_ids dict
        section_ids_dict = {}
        if prothom_alo_sections and 'prothom_alo' in (sources or []):
            section_ids_dict['prothom_alo'] = prothom_alo_sections
            logger.info(f"  - Will use {len(prothom_alo_sections)} section groups for Prothom Alo")
        
        # Generate job ID
        job_id = f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting background scraping job {job_id}")
        logger.info(f"  - sources={sources}")
        logger.info(f"  - dates={start_dt} to {end_dt}")
        logger.info(f"  - section_ids={section_ids_dict}")
        
        # Start scraping in background
        background_tasks.add_task(
            run_scraping_task, 
            job_id, 
            sources or [], 
            start_dt, 
            end_dt,
            section_ids_dict or None
        )
        
        return {
            "status": "started",
            "job_id": job_id,
            "message": f"Scraping started in background for {len(sources) if sources else 'all'} newspaper(s).",
            "sources": sources,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "prothom_alo_sections": prothom_alo_sections if prothom_alo_sections else "using defaults"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual scrape error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/scrape/status/{job_id}")
async def get_scraping_status(job_id: str):
    """Get status of a scraping job."""
    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return scraping_jobs[job_id]


@router.get("/scrape/jobs")
async def get_all_scraping_jobs():
    """Get all scraping jobs."""
    return scraping_jobs


@router.get("/articles")
async def get_articles(
    db: Session = Depends(get_db),
    source: Optional[str] = Query(None, description="Filter by newspaper source"),
    is_biased: Optional[bool] = Query(None, description="Filter by bias status"),
    processed: Optional[bool] = Query(None, description="Filter by processing status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return")
):
    """
    Get articles from database with filtering and pagination.
    
    Returns article list with bias analysis and debiasing results.
    """
    try:
        query = db.query(Article)
        
        # Apply filters
        if source:
            query = query.filter(Article.source == source)
        if is_biased is not None:
            query = query.filter(Article.is_biased == is_biased)
        if processed is not None:
            query = query.filter(Article.processed == processed)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        articles = query.order_by(Article.scraped_at.desc()).offset(skip).limit(limit).all()
        
        # Format response
        result = []
        for article in articles:
            result.append({
                "id": article.id,
                "source": article.source,
                "url": article.url,
                "title": article.title,
                "original_content": article.original_content,
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "scraped_at": article.scraped_at.isoformat(),
                "is_biased": article.is_biased,
                "bias_score": article.bias_score,
                "bias_summary": article.bias_summary,
                "biased_terms": article.biased_terms,
                "debiased_content": article.debiased_content,
                "changes_made": article.changes_made,
                "total_changes": article.total_changes,
                "recommended_headline": article.recommended_headline,
                "processed": article.processed,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None,
                "processing_error": article.processing_error
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "articles": result
        }
    
    except Exception as e:
        logger.error(f"Get articles error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch articles: {str(e)}")


@router.get("/articles/{article_id}")
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific article including full bias analysis.
    """
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return {
            "id": article.id,
            "source": article.source,
            "url": article.url,
            "title": article.title,
            "original_content": article.original_content,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "scraped_at": article.scraped_at.isoformat(),
            "is_biased": article.is_biased,
            "bias_score": article.bias_score,
            "bias_summary": article.bias_summary,
            "biased_terms": article.biased_terms,
            "debiased_content": article.debiased_content,
            "changes_made": article.changes_made,
            "total_changes": article.total_changes,
            "generated_headlines": article.generated_headlines,
            "recommended_headline": article.recommended_headline,
            "processed": article.processed,
            "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            "processing_error": article.processing_error
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get article error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {str(e)}")


@router.post("/articles/{article_id}/reprocess")
async def reprocess_article(article_id: int, db: Session = Depends(get_db)):
    """
    Re-process a specific article to apply debiasing again.
    Useful after code updates to fix articles that weren't properly debiased.
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
