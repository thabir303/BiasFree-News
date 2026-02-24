"""
⚠️ DEPRECATED — This file is NOT mounted in main.py.
Batch TOON endpoints have been consolidated into routes_enhanced.py.
Kept for reference only. Do not add new endpoints here.

Original: Enhanced API routes for batch bias detection with TOON format optimization.
Supports processing up to 20 articles in a single request with 30-60% token reduction.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
from app.services.enhanced_article_processor import EnhancedArticleProcessor
from app.models.enhanced_schemas import (
    BatchArticleInput,
    BatchBiasAnalysisResponse,
    EnhancedProcessingStats,
    ScrapedArticle
)
from app.models.schemas import ArticleInput, BiasAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enhanced", tags=["enhanced"])

# Initialize enhanced services
enhanced_bias_detector = EnhancedBiasDetectorService()


@router.post("/analyze-batch", response_model=BatchBiasAnalysisResponse)
async def analyze_articles_batch(
    request: BatchArticleInput,
    db: Session = Depends(get_db)
) -> BatchBiasAnalysisResponse:
    """
    Analyze multiple articles for bias in a single LLM call.
    
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
        
        # Convert input articles to format suitable for analysis
        articles_data = []
        for article in request.articles:
            articles_data.append({
                "id": f"article_{len(articles_data)}",  # Generate unique ID
                "title": article.title or "Untitled",
                "content": article.content,
                "source": "user_input"
            })
        
        # Perform batch bias analysis
        result = await enhanced_bias_detector.analyze_bias_batch(
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


@router.post("/process-scraped-batch", response_model=EnhancedProcessingStats)
async def process_scraped_articles_batch(
    max_articles: int = Query(20, ge=1, le=100, description="Maximum articles to process"),
    use_enhanced: bool = Query(True, description="Use enhanced TOON-based processing"),
    db: Session = Depends(get_db)
) -> EnhancedProcessingStats:
    """
    Process scraped articles from database in optimized batches.
    
    Features:
    - Processes up to 20 articles per LLM call
    - Uses TOON format for token efficiency
    - Batch processing for cost optimization
    - Automatic fallback to individual processing
    
    Args:
        max_articles: Maximum number of articles to process (1-100)
        use_enhanced: Whether to use enhanced TOON-based processing
        db: Database session
        
    Returns:
        Processing statistics with batch metrics
        
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


@router.get("/toon-demo")
async def toon_format_demo() -> Dict[str, Any]:
    """
    Demonstrate TOON format efficiency compared to JSON.
    
    Returns:
        Comparison showing token savings achieved by TOON format
    """
    try:
        from app.utils.enhanced_toon_formatter import enhanced_toon_formatter
        
        # Sample data
        sample_articles = [
            {
                "id": "1",
                "title": "রাজনৈতিক দলের নেতা বলেছেন",
                "content": "আজকের রাজনৈতিক পরিস্থিতি খুবই উত্তপ্ত। বিরোধী দলগুলো সরকারের বিরুদ্ধে কঠোর অবস্থান নিয়েছে।",
                "source": "sample_news",
                "date": "2024-01-09"
            },
            {
                "id": "2", 
                "title": "অর্থনৈতিক প্রবৃদ্ধির খবর",
                "content": "দেশের অর্থনীতি দ্রুত উন্নতি করছে। বিশেষজ্ঞরা বলছেন এই প্রবৃদ্ধি টেকসই হবে।",
                "source": "sample_news",
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
            "description": "TOON format reduces token usage by declaring keys once and streaming values as rows"
        }
        
    except Exception as e:
        logger.error(f"TOON demo failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TOON demo failed: {str(e)}")


@router.get("/stats")
async def get_processing_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get processing statistics and system status.
    
    Args:
        db: Database session
        
    Returns:
        Processing statistics and system metrics
    """
    try:
        from app.database.models import Article
        
        # Get article statistics
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
                "token_reduction": "30-60%"
            }
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")