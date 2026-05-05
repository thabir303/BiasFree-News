"""
Enhanced API routes with database integration and scheduler control.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.schemas import (
    ArticleInput,
    FullProcessResponse
)
from app.database.database import get_db
from app.database.models import Article, User
from app.services.bias_detector import BiasDetectorService
from app.services.scheduler import get_scheduler
from app.services.article_processor import ArticleProcessor
from app.services.auth_service import require_admin, require_authenticated, get_current_user
from app.config import settings
from app.config.newspapers import get_all_newspaper_keys

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create API router
router = APIRouter(prefix="/api", tags=["bias-detection"])

# Initialize services
bias_detector = BiasDetectorService()


@router.post("/full-process", response_model=FullProcessResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def full_process(
    request: Request,
    article: ArticleInput,
    current_user: User = Depends(require_authenticated)
) -> FullProcessResponse:
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


@router.post("/scrape/manual")
async def manual_scrape(
    sources: Optional[List[str]] = Query(None, alias="sources[]"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Manual scraping endpoint for on-demand article collection.
    Compatible with frontend query parameters.
    
    - **sources**: List of newspaper sources
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    """
    try:
        from app.services.scheduler import get_scheduler
        
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        
        # Get scheduler instance
        scheduler = get_scheduler()
        
        # Trigger manual scraping (without automatic processing)
        result = await scheduler.run_manual_scraping(
            sources=sources,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "status": "completed",
            "message": "Scraping completed successfully",
            "statistics": result
        }
        
    except Exception as e:
        logger.error(f"Manual scraping error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Manual scraping failed: {str(e)}")


@router.get("/articles")
async def get_articles(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    processed: Optional[bool] = Query(None, description="Filter by processing status"),
    biased: Optional[bool] = Query(None, alias="is_biased", description="Filter by bias status"),
    source: Optional[str] = Query(None, description="Filter by news source"),
    category: Optional[str] = Query(None, description="Filter by category (রাজনীতি, বিশ্ব, মতামত, বাংলাদেশ)"),
    date_from: Optional[str] = Query(None, description="Filter articles published on or after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter articles published on or before this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search articles by title (case-insensitive partial match)"),
    sort_by: Optional[str] = Query(None, description="Sort by: newest, oldest, bias_high, bias_low"),
):
    """
    Get articles with filtering and pagination.
    
    - **skip**: Number of articles to skip
    - **limit**: Maximum articles to return (1-100)
    - **processed**: Filter by processing status
    - **biased**: Filter by bias detection result
    - **source**: Filter by news source
    - **category**: Filter by article category
    - **date_from**: Filter by published date (from, inclusive) — YYYY-MM-DD
    - **date_to**: Filter by published date (to, inclusive) — YYYY-MM-DD
    """
    try:
        query = db.query(Article) # create base query
        
        # Apply filters
        if processed is not None:
            query = query.filter(Article.processed == processed)
        if biased is not None:
            query = query.filter(Article.is_biased == biased)
        if source:
            query = query.filter(Article.source == source)
        if category:
            query = query.filter(Article.category == category)
        if date_from:
            try:
                df = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Article.published_date >= df)
            except ValueError:
                raise HTTPException(status_code=400, detail="date_from must be YYYY-MM-DD")
        if date_to:
            try:
                dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                query = query.filter(Article.published_date <= dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="date_to must be YYYY-MM-DD")
        if search:
            query = query.filter(
                (Article.title.ilike(f"%{search}%")) |
                (Article.original_content.ilike(f"%{search}%"))
            )
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if sort_by == 'oldest':
            query = query.order_by(Article.created_at.asc())
        elif sort_by == 'bias_high':
            query = query.order_by(Article.bias_score.desc().nullslast())
        elif sort_by == 'bias_low':
            query = query.order_by(Article.bias_score.asc().nullslast())
        else:  # default: newest
            query = query.order_by(Article.created_at.desc())
        
        # Get articles with pagination
        articles = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        result = []
        for article in articles:
            result.append({
                "id": article.id,
                "title": article.title,
                "content": article.original_content[:500] + "..." if len(article.original_content) > 500 else article.original_content,
                "original_content": article.original_content[:500] + "..." if len(article.original_content) > 500 else article.original_content,
                "source": article.source,
                "category": article.category,
                "url": article.url,
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "scraped_at": article.scraped_at.isoformat() if article.scraped_at else article.created_at.isoformat(),
                "processed": article.processed,
                "is_biased": article.is_biased if article.is_biased is not None else False,
                "bias_score": article.bias_score if article.bias_score is not None else 0.0,
                "total_changes": article.total_changes if article.total_changes else 0,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None,
                "created_at": article.created_at.isoformat(),
                "cluster_id": article.cluster_id,
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
    If the article belongs to a cluster, includes the unified/merged content,
    all sibling articles, and pairwise similarity percentages.
    """
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        result = {
            "id": article.id,
            "title": article.title,
            "content": article.original_content,
            "original_content": article.original_content,
            "debiased_content": article.debiased_content,
            "source": article.source,
            "category": article.category,
            "url": article.url,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "scraped_at": article.scraped_at.isoformat() if article.scraped_at else article.created_at.isoformat(),
            "processed": article.processed,
            "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            "processing_error": article.processing_error,
            "is_biased": article.is_biased if article.is_biased is not None else False,
            "bias_score": article.bias_score if article.bias_score is not None else 0.0,
            "bias_summary": article.bias_summary,
            "biased_terms": article.biased_terms if article.biased_terms else [],
            "changes_made": article.changes_made if article.changes_made else [],
            "total_changes": article.total_changes if article.total_changes else 0,
            "generated_headlines": article.generated_headlines,
            "recommended_headline": article.recommended_headline,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat() if article.updated_at else None,
            "cluster_id": article.cluster_id,
            # Cluster/merge info — populated below if article is clustered
            "cluster_info": None,
        }

        # ── Populate cluster info if article belongs to a cluster ──
        if article.cluster_id:
            from app.database.models import ArticleCluster

            cluster = db.query(ArticleCluster).filter(
                ArticleCluster.id == article.cluster_id
            ).first()

            if cluster:
                sibling_articles = db.query(Article).filter(
                    Article.cluster_id == article.cluster_id
                ).all()

                # Build similarity lookup from precomputed data
                sim_lookup: Dict[tuple, float] = {}
                if cluster.pairwise_similarities:
                    for p in cluster.pairwise_similarities:
                        sim_lookup[(p["a"], p["b"])] = p["sim"]
                        sim_lookup[(p["b"], p["a"])] = p["sim"]

                siblings_info = []
                for sib in sibling_articles:
                    if sib.id == article.id:
                        continue  # skip self
                    sim_pct = None
                    pre = sim_lookup.get((article.id, sib.id))
                    if pre is not None:
                        sim_pct = round(pre * 100, 1)

                    siblings_info.append({
                        "id": sib.id,
                        "title": sib.title,
                        "source": sib.source,
                        "category": sib.category,
                        "url": sib.url,
                        "original_content": sib.original_content[:500] + "..." if sib.original_content and len(sib.original_content) > 500 else sib.original_content,
                        "is_biased": sib.is_biased if sib.is_biased is not None else False,
                        "bias_score": sib.bias_score if sib.bias_score is not None else 0.0,
                        "processed": sib.processed,
                        "scraped_at": sib.scraped_at.isoformat() if sib.scraped_at else None,
                        "similarity_percent": sim_pct,
                    })

                result["cluster_info"] = {
                    "cluster_id": cluster.id,
                    "cluster_label": cluster.cluster_label,
                    "article_count": cluster.article_count,
                    "avg_similarity": cluster.avg_similarity,
                    "sources": cluster.sources or [],
                    "category": cluster.category,
                    "unified_content": cluster.unified_content,
                    "unified_headline": cluster.unified_headline,
                    "merged_articles": siblings_info,
                }

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get article error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {str(e)}")


@router.post("/articles/{article_id}/process")
async def process_article_endpoint(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Process a single unprocessed article for bias detection and debiasing.
    
    - **article_id**: Article ID to process
    
    Returns the updated article with bias analysis results.
    """
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        if article.processed:
            logger.info(f"Article {article_id} already processed, returning current data")
            # Return current article data
            return {
                "id": article.id,
                "title": article.title,
                "source": article.source,
                "url": article.url,
                "original_content": article.original_content,
                "debiased_content": article.debiased_content,
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "scraped_at": article.scraped_at.isoformat() if article.scraped_at else article.created_at.isoformat(),
                "processed": article.processed,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None,
                "processing_error": article.processing_error,
                "is_biased": article.is_biased if article.is_biased is not None else False,
                "bias_score": article.bias_score if article.bias_score is not None else 0.0,
                "bias_summary": article.bias_summary,
                "biased_terms": article.biased_terms,
                "changes_made": article.changes_made,
                "total_changes": article.total_changes if article.total_changes else 0,
                "recommended_headline": article.recommended_headline,
                "generated_headlines": article.generated_headlines,
                "created_at": article.created_at.isoformat(),
                "updated_at": article.updated_at.isoformat() if article.updated_at else None
            }
        
        # Process the article
        logger.info(f"Processing article {article_id} for bias detection...")
        processor = ArticleProcessor(db)
        result = await processor.process_article(article)
        
        # Refresh article from db to get updated data
        db.refresh(article)
        
        logger.info(f"Article {article_id} processed: biased={result['biased']}, changes={result['changes_made']}")
        
        # Return updated article data
        return {
            "id": article.id,
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "original_content": article.original_content,
            "debiased_content": article.debiased_content,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "scraped_at": article.scraped_at.isoformat() if article.scraped_at else article.created_at.isoformat(),
            "processed": article.processed,
            "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            "processing_error": article.processing_error,
            "is_biased": article.is_biased if article.is_biased is not None else False,
            "bias_score": article.bias_score if article.bias_score is not None else 0.0,
            "bias_summary": article.bias_summary,
            "biased_terms": article.biased_terms,
            "changes_made": article.changes_made,
            "total_changes": article.total_changes if article.total_changes else 0,
            "recommended_headline": article.recommended_headline,
            "generated_headlines": article.generated_headlines,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat() if article.updated_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process article error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process article: {str(e)}")


@router.post("/articles/{article_id}/reprocess")
async def reprocess_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Reprocess a specific article — re-run bias analysis from scratch.
    Available to any authenticated user.
    
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
    limit: int = Query(50, ge=1, le=200, description="Max articles to reprocess"),
    current_user: User = Depends(require_admin)
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
async def get_scheduler_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Get scheduler status, recent job history, and last run details."""
    try:
        from app.services.scheduler import get_scheduler

        scheduler = get_scheduler()
        status = scheduler.get_status(db=db)

        return {
            "running": status["running"],
            "next_run": status["next_run"],
            "schedule": status["schedule"],
            "last_run": status["last_run"]
        }
    
    except Exception as e:
        logger.error(f"Scheduler status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/scheduler/update")
async def update_scheduler(
    hour: int = Query(..., ge=0, le=23, description="Hour (0-23) in BDT"),
    minute: int = Query(..., ge=0, le=59, description="Minute (0-59)"),
    current_user: User = Depends(require_admin)
):
    """Update the scheduler configuration (Admin only)."""
    try:
        from app.services.scheduler import get_scheduler

        scheduler = get_scheduler()
        success = scheduler.update_schedule(hour, minute)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update schedule")
        
        return {
            "message": f"Scheduler updated to run daily at {hour:02d}:{minute:02d} BDT",
            "hour": hour,
            "minute": minute,
            "schedule": f"Daily at {hour:02d}:{minute:02d} BDT"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update scheduler error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update scheduler: {str(e)}")


@router.post("/scheduler/toggle")
async def toggle_scheduler(
    current_user: User = Depends(require_admin)
):
    """Toggle scheduler on/off (Admin only). Pauses or resumes the APScheduler."""
    try:
        from app.services.scheduler import get_scheduler

        scheduler = get_scheduler()
        now_running = scheduler.toggle()

        if now_running:
            return {
                "running": True,
                "message": "Scheduler resumed successfully. Automatic scraping will continue on schedule."
            }
        else:
            return {
                "running": False,
                "message": "Scheduler paused successfully. No automatic scraping will occur until resumed."
            }
    
    except Exception as e:
        logger.error(f"Toggle scheduler error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle scheduler: {str(e)}")


@router.get("/newspapers")
async def get_newspapers():
    """Get list of configured newspapers."""
    try:
        # Cache for 5 minutes — newspaper config rarely changes
        cached = _get_cached("newspapers")
        if cached:
            return cached

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
        
        result = {"newspapers": newspapers}
        _set_cached("newspapers", result, ttl=300)
        return result
    
    except Exception as e:
        logger.error(f"Get newspapers error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch newspapers: {str(e)}")


# ── Simple in-memory TTL cache ──────────────────────────────────────
import time as _time
_cache: Dict[str, Any] = {}  # key -> {"data": ..., "expires": float}

def _get_cached(key: str) -> Any:
    entry = _cache.get(key)
    if entry and entry["expires"] > _time.time():
        return entry["data"]
    return None

def _set_cached(key: str, data: Any, ttl: int = 300):
    _cache[key] = {"data": data, "expires": _time.time() + ttl}


@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Get overall statistics about scraped and processed articles."""
    try:
        # Check cache first (30s TTL)
        cached = _get_cached("statistics")
        if cached:
            return cached

        from sqlalchemy import func, case

        # Single query: total, processed, biased counts + per-source counts
        stats_row = db.query(
            func.count(Article.id).label("total"),
            func.sum(case((Article.processed == True, 1), else_=0)).label("processed"),
            func.sum(case((Article.is_biased == True, 1), else_=0)).label("biased"),
        ).one()

        total_articles = stats_row.total or 0
        processed_articles = int(stats_row.processed or 0)
        biased_articles = int(stats_row.biased or 0)

        # GROUP BY source instead of N+1 queries
        source_rows = db.query(
            Article.source, func.count(Article.id)
        ).group_by(Article.source).all()
        by_source = {src: cnt for src, cnt in source_rows}

        result = {
            "total_articles": total_articles,
            "processed_articles": processed_articles,
            "processed_count": processed_articles,
            "biased_articles": biased_articles,
            "biased_count": biased_articles,
            "unprocessed_articles": total_articles - processed_articles,
            "by_source": by_source
        }
        _set_cached("statistics", result, ttl=30)
        return result

    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


@router.get("/analytics/visualization")
async def get_visualization_data(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Get data for visualization charts: bias distribution, source comparison, time-series, category breakdown."""
    try:
        from sqlalchemy import func, case

        # 1. Bias score distribution (histogram buckets)
        processed_articles = db.query(Article.bias_score).filter(
            Article.processed == True,
            Article.bias_score.isnot(None)
        ).all()
        scores = [float(r[0]) for r in processed_articles if r[0] is not None]

        buckets = [0] * 10  # 0-9, 10-19, ..., 90-100
        for s in scores:
            idx = min(int(s // 10), 9)
            buckets[idx] += 1
        bias_distribution = [{"range": f"{i*10}-{i*10+9}" if i < 9 else "90-100", "count": buckets[i]} for i in range(10)]

        # 2. Source-level bias comparison
        source_stats = db.query(
            Article.source,
            func.count(Article.id).label("total"),
            func.avg(case((Article.processed == True, Article.bias_score), else_=None)).label("avg_bias"),
            func.sum(case((Article.is_biased == True, 1), else_=0)).label("biased_count"),
            func.sum(case((Article.processed == True, 1), else_=0)).label("processed_count"),
        ).group_by(Article.source).all()

        source_comparison = []
        for row in source_stats:
            source_comparison.append({
                "source": row.source,
                "total": row.total,
                "avg_bias": round(float(row.avg_bias or 0), 2),
                "biased_count": int(row.biased_count or 0),
                "processed_count": int(row.processed_count or 0),
                "bias_rate": round(int(row.biased_count or 0) / max(int(row.processed_count or 0), 1) * 100, 1),
            })

        # 3. Time-series: articles per day + bias rate over time
        cutoff = datetime.utcnow() - timedelta(days=days)
        daily_rows = db.query(
            func.date(Article.scraped_at).label("day"),
            func.count(Article.id).label("total"),
            func.sum(case((Article.is_biased == True, 1), else_=0)).label("biased"),
            func.sum(case((Article.processed == True, 1), else_=0)).label("processed"),
        ).filter(
            Article.scraped_at >= cutoff,
            Article.scraped_at.isnot(None),
        ).group_by("day").order_by("day").all()

        time_series = []
        for row in daily_rows:
            if row.day is None:
                continue
            day_str = row.day if isinstance(row.day, str) else row.day.isoformat()
            time_series.append({
                "date": day_str,
                "total": row.total,
                "biased": int(row.biased or 0),
                "processed": int(row.processed or 0),
                "bias_rate": round(int(row.biased or 0) / max(int(row.processed or 0), 1) * 100, 1),
            })

        # 4. Per-category breakdown
        category_rows = db.query(
            Article.category,
            func.count(Article.id).label("total"),
            func.sum(case((Article.is_biased == True, 1), else_=0)).label("biased"),
            func.sum(case((Article.processed == True, 1), else_=0)).label("processed"),
            func.avg(case((Article.processed == True, Article.bias_score), else_=None)).label("avg_bias"),
        ).filter(Article.category.isnot(None)).group_by(Article.category).all()

        category_breakdown = []
        for row in category_rows:
            category_breakdown.append({
                "category": row.category,
                "total": row.total,
                "biased": int(row.biased or 0),
                "processed": int(row.processed or 0),
                "avg_bias": round(float(row.avg_bias or 0), 2),
                "bias_rate": round(int(row.biased or 0) / max(int(row.processed or 0), 1) * 100, 1),
            })

        return {
            "bias_distribution": bias_distribution,
            "source_comparison": source_comparison,
            "time_series": time_series,
            "category_breakdown": category_breakdown,
        }

    except Exception as e:
        logger.error(f"Visualization data error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch visualization data: {str(e)}")


# ============================================
# Article Clustering Endpoints
# ============================================
from app.services.clustering_service import ClusteringService


@router.get("/clusters")
async def get_clusters(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter clusters by category"),
    min_articles: int = Query(2, ge=2, le=50, description="Minimum articles in cluster"),
):
    """
    Get list of article clusters with pagination and filtering.
    Clusters group similar articles from different newspapers covering the same event.
    """
    try:
        service = ClusteringService(db)
        clusters, total = service.get_all_clusters(
            skip=skip, limit=limit, category=category, min_articles=min_articles
        )
        return {
            "clusters": clusters,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Get clusters error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clusters: {str(e)}")


@router.get("/clusters/stats")
async def get_clustering_stats(db: Session = Depends(get_db)):
    """Get article clustering statistics."""
    try:
        cached = _get_cached("clustering_stats")
        if cached:
            return cached
        service = ClusteringService(db)
        result = service.get_clustering_stats()
        _set_cached("clustering_stats", result, ttl=60)
        return result
    except Exception as e:
        logger.error(f"Clustering stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clustering stats: {str(e)}")


@router.get("/clusters/{cluster_id}")
async def get_cluster_detail(cluster_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific cluster.
    Includes all articles, pairwise similarities, and unified content (if generated).
    """
    try:
        service = ClusteringService(db)
        detail = service.get_cluster_detail(cluster_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Cluster not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get cluster detail error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster: {str(e)}")


@router.post("/clusters/generate")
async def generate_clusters(
    background_tasks: BackgroundTasks,
    days_back: int = Query(3, ge=1, le=30, description="How many days back to look for articles"),
    re_cluster: bool = Query(False, description="Re-cluster all articles (removes existing clusters)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Trigger article clustering. Groups similar articles from different sources.
    Uses paraphrase-multilingual-MiniLM-L12-v2 for semantic similarity.
    
    - **days_back**: How many days back to look for unclustered articles
    - **re_cluster**: If True, removes existing clusters and re-clusters everything
    """
    try:
        service = ClusteringService(db)
        result = service.cluster_articles(days_back=days_back, re_cluster_all=re_cluster)
        return {
            "status": "completed",
            "message": "Article clustering completed (multi-stage with extractive summarization)",
            "statistics": result
        }
    except Exception as e:
        logger.error(f"Cluster generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@router.post("/clusters/{cluster_id}/regenerate-summary")
async def regenerate_cluster_summary(
    cluster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Regenerate extractive unified summary for a specific cluster.
    Uses sumy (LSA + TextRank ensemble) — pure extractive, no API.
    """
    try:
        service = ClusteringService(db)
        result = service.regenerate_summary(cluster_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cluster not found")
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regenerate summary error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary regeneration failed: {str(e)}")


@router.post("/clusters/{cluster_id}/debias-unified")
async def debias_unified_content(
    cluster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Run bias detection and debiasing on a cluster's unified content.
    Returns the debiased unified article.
    """
    try:
        from app.database.models import ArticleCluster

        cluster = db.query(ArticleCluster).filter(ArticleCluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        if not cluster.unified_content:
            raise HTTPException(status_code=400, detail="No unified content to debias")

        bias_detector = BiasDetectorService()

        # Step 1: Analyze for bias
        analysis = await bias_detector.analyze_bias(
            cluster.unified_content,
            cluster.unified_headline
        )

        result = {
            "cluster_id": cluster_id,
            "is_biased": analysis.is_biased,
            "bias_score": analysis.bias_score,
            "bias_summary": analysis.summary,
            "biased_terms": [t.model_dump() for t in analysis.biased_terms],
            "debiased_content": None,
            "changes": [],
            "total_changes": 0,
        }

        # Step 2: Debias if biased
        if analysis.is_biased:
            debiased = await bias_detector.debias_article(
                cluster.unified_content,
                [t.model_dump() for t in analysis.biased_terms]
            )
            result["debiased_content"] = debiased.debiased_content
            result["changes"] = [c.model_dump() for c in debiased.changes]
            result["total_changes"] = debiased.total_changes

            # Optionally store debiased content on the cluster
            cluster.debiased_unified_content = debiased.debiased_content
            db.commit()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debias unified error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debiasing failed: {str(e)}")