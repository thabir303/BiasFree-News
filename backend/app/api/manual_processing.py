"""
Manual bias analysis endpoints for on-demand article processing.
Articles are scraped without processing, then analyzed individually via button clicks.
"""

import logging
from typing import Optional, Any, Dict
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database.database import get_db
from app.database.models import Article
from app.models.schemas import BiasAnalysisResponse, DebiasResponse, HeadlineResponse
from app.services.bias_detector import BiasDetectorService
from app.config import settings
from app.config.newspapers import get_all_newspaper_keys

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create API router for manual processing
router = APIRouter(prefix="/api/manual", tags=["manual-processing"])

# Initialize bias detector service
bias_detector = BiasDetectorService()


@router.post("/scrape-only")
async def scrape_articles_only(
    background_tasks: BackgroundTasks,
    newspapers: Optional[list[str]] = Query(None, description="Specific newspapers to scrape"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    max_articles: int = Query(50, ge=1, le=500, description="Maximum articles per newspaper"),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Scrape articles from newspapers WITHOUT automatic processing.
    Articles are stored for manual bias analysis later.
    
    - **newspapers**: Optional list of newspaper keys (scrapes all if empty)
    - **start_date**: Optional start date (defaults to today)
    - **end_date**: Optional end date (defaults to today)
    - **max_articles**: Maximum articles per newspaper (1-500)
    
    Returns scraping statistics with unprocessed article count.
    """
    try:
        from app.services.manual_only_scraper import scrape_multiple_newspapers_manual
        
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
        
        logger.info(f"Starting manual scrape for {len(newspapers)} newspapers, dates: {start_date} to {end_date}")
        
        # Start scraping in background (NO automatic processing)
        background_tasks.add_task(
            scrape_multiple_newspapers_manual,
            newspapers=newspapers,
            start_date=start_date,
            end_date=end_date,
            max_articles_per_newspaper=max_articles,
            db=db
        )
        
        return {
            "status": "started",
            "message": f"Manual scraping started for {len(newspapers)} newspapers",
            "newspapers": newspapers,
            "date_range": f"{start_date} to {end_date}",
            "max_articles_per_newspaper": max_articles,
            "processing_mode": "manual-only (no automatic analysis)",
            "note": "Articles will be stored unprocessed for manual bias analysis"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual scrape endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual scraping failed: {str(e)}")


@router.post("/analyze-article/{article_id}", response_model=BiasAnalysisResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_article_manual(
    request: Request,
    article_id: int,
    use_toon_format: bool = Query(False, description="Use TOON format for LLM efficiency"),
    db: Session = Depends(get_db)
) -> BiasAnalysisResponse:
    """
    Manually analyze a single article for bias.
    
    - **article_id**: Article ID to analyze
    - **use_toon_format**: Whether to use TOON format (default: False for compatibility)
    
    Returns bias analysis results using existing prompts.
    """
    try:
        # Get article from database
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        logger.info(f"Manual bias analysis for article {article_id}: '{article.title[:50]}...'")
        
        # Use existing bias detector with optional TOON format
        if use_toon_format:
            # Use enhanced TOON-based detection for efficiency
            from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
            enhanced_detector = EnhancedBiasDetectorService()
            
            result = await enhanced_detector.analyze_single_article(
                content=article.original_content,
                title=article.title,
                article_id=str(article.id),
                use_toon_format=True
            )
            
            logger.info(f"TOON format used - Token savings achieved")
            
        else:
            # Use existing bias detector (original prompts)
            result = await bias_detector.analyze_bias(
                article.original_content,
                article.title
            )
            
            logger.info(f"Original format used - Existing prompts")
        
        # Update article with analysis results
        article.is_biased = result.is_biased
        article.bias_score = result.bias_score
        article.bias_summary = result.summary
        article.biased_terms = [term.model_dump() for term in result.biased_terms]
        article.processed = True
        article.processed_at = datetime.utcnow()
        article.processing_error = None
        
        db.commit()
        
        logger.info(
            f"Manual analysis complete for article {article_id}: "
            f"biased={result.is_biased}, score={result.bias_score}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Manual analysis failed for article {article_id}: {str(e)}"
        logger.error(error_msg)
        
        # Update article with error
        if 'article' in locals():
            article.processed = True
            article.processed_at = datetime.utcnow()
            article.processing_error = error_msg
            db.commit()
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/debias-article/{article_id}")
async def debias_article_manual(
    request: Request,
    article_id: int,
    use_toon_format: bool = Query(False, description="Use TOON format for LLM efficiency"),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Manually debias a single article (if biased).
    
    - **article_id**: Article ID to debias
    - **use_toon_format**: Whether to use TOON format (default: False for compatibility)
    
    Returns debiasing results and updates article.
    """
    try:
        # Get article from database
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if article was analyzed
        if not article.processed:
            raise HTTPException(status_code=400, detail="Article must be analyzed first")
        
        if not article.is_biased:
            return {
                "status": "success",
                "message": "Article is not biased - no debiasing needed",
                "changes_made": 0,
                "debiased_content": article.original_content
            }
        
        logger.info(f"Manual debiasing for article {article_id}: '{article.title[:50]}...'")
        
        # Use existing debias functionality
        biased_terms = [term.model_dump() for term in article.biased_terms] if article.biased_terms else None
        
        result = await bias_detector.debias_article(
            article.original_content,
            biased_terms
        )
        
        # Update article with debiasing results
        article.debiased_content = result.debiased_content
        article.changes_made = [change.model_dump() for change in result.changes_made]
        article.total_changes = result.total_changes
        
        # Generate neutral headline
        try:
            headline_result = await bias_detector.generate_neutral_headline(
                result.debiased_content,
                article.title
            )
            article.generated_headlines = headline_result.generated_headlines
            article.recommended_headline = headline_result.recommended_headline
        except Exception as e:
            logger.warning(f"Headline generation failed for article {article_id}: {str(e)}")
        
        db.commit()
        
        logger.info(
            f"Manual debiasing complete for article {article_id}: "
            f"{result.total_changes} changes made"
        )
        
        return {
            "status": "success",
            "message": f"Article debiased successfully with {result.total_changes} changes",
            "changes_made": result.total_changes,
            "debiased_content": result.debiased_content,
            "original_content": result.original_content,
            "bias_reduction_score": result.bias_reduction_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Manual debiasing failed for article {article_id}: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/unprocessed-articles")
async def get_unprocessed_articles(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    source: Optional[str] = Query(None, description="Filter by news source")
) -> dict[str, Any]:
    """
    Get unprocessed articles that need manual bias analysis.
    
    - **skip**: Number of articles to skip
    - **limit**: Maximum articles to return (1-100)
    - **source**: Filter by news source
    
    Returns list of articles ready for manual analysis.
    """
    try:
        query = db.query(Article).filter(Article.processed == False)
        
        if source:
            query = query.filter(Article.source == source)
        
        total = query.count()
        
        articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
        
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
                "scraped_at": article.scraped_at.isoformat() if article.scraped_at else None,
                "ready_for_analysis": True
            })
        
        return {
            "articles": result,
            "total": total,
            "skip": skip,
            "limit": limit,
            "message": f"{total} articles ready for manual bias analysis"
        }
        
    except Exception as e:
        logger.error(f"Get unprocessed articles error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch unprocessed articles: {str(e)}")


@router.post("/batch-analyze-unprocessed")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def batch_analyze_unprocessed(
    request: Request,
    max_articles: int = Query(20, ge=1, le=100, description="Maximum articles to analyze"),
    use_toon_format: bool = Query(True, description="Use TOON format for efficiency"),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Batch analyze multiple unprocessed articles.
    
    - **max_articles**: Maximum articles to analyze (1-100, default: 20)
    - **use_toon_format**: Use TOON format for token efficiency (default: True)
    
    Returns batch analysis statistics.
    """
    try:
        # Get unprocessed articles
        articles = db.query(Article).filter(
            Article.processed == False
        ).limit(max_articles).all()
        
        if not articles:
            return {
                "status": "success",
                "message": "No unprocessed articles found",
                "analyzed": 0,
                "failed": 0
            }
        
        logger.info(f"Batch analyzing {len(articles)} unprocessed articles")
        
        analyzed_count = 0
        failed_count = 0
        
        for article in articles:
            try:
                # Use enhanced bias detector for batch processing
                if use_toon_format:
                    from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
                    enhanced_detector = EnhancedBiasDetectorService()
                    
                    result = await enhanced_detector.analyze_single_article(
                        content=article.original_content,
                        title=article.title,
                        article_id=str(article.id),
                        use_toon_format=True
                    )
                else:
                    # Use existing bias detector
                    result = await bias_detector.analyze_bias(
                        article.original_content,
                        article.title
                    )
                
                # Update article with results
                article.is_biased = result.is_biased
                article.bias_score = result.bias_score
                article.bias_summary = result.summary
                article.biased_terms = [term.model_dump() for term in result.biased_terms]
                article.processed = True
                article.processed_at = datetime.utcnow()
                article.processing_error = None
                
                analyzed_count += 1
                
            except Exception as e:
                error_msg = f"Analysis failed for article {article.id}: {str(e)}"
                logger.error(error_msg)
                
                article.processed = True
                article.processed_at = datetime.utcnow()
                article.processing_error = error_msg
                
                failed_count += 1
        
        db.commit()
        
        logger.info(f"Batch analysis complete: {analyzed_count} analyzed, {failed_count} failed")
        
        return {
            "status": "success",
            "message": f"Batch analysis complete: {analyzed_count} analyzed, {failed_count} failed",
            "analyzed": analyzed_count,
            "failed": failed_count,
            "toon_format_used": use_toon_format
        }
        
    except Exception as e:
        logger.error(f"Batch analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")