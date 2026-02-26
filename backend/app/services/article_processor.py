"""
Article processing service for bias detection and debiasing.
Processes scraped articles from database.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.models import Article
from app.services.bias_detector import BiasDetectorService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Delay between LLM calls (seconds) to respect rate limits
LLM_DELAY_SECONDS = 2


class ArticleProcessor:
    """Service for processing articles with bias detection and debiasing."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.bias_detector = BiasDetectorService()
        self.openai_service = OpenAIService()
    
    async def process_article(self, article: Article) -> Dict[str, Any]:
        """
        Process a single article: detect bias and debias if needed.
        
        Args:
            article: Article database model
        
        Returns:
            Processing statistics
        """
        stats = {
            "article_id": article.id,
            "success": False,
            "biased": False,
            "changes_made": 0,
            "error": None
        }
        
        try:
            # Step 1: Analyze for bias
            analysis = await self.bias_detector.analyze_bias(
                article.original_content,
                article.title
            )
            
            # Update article with analysis results
            article.is_biased = analysis.is_biased
            article.bias_score = analysis.bias_score
            article.bias_summary = analysis.summary
            article.biased_terms = [term.model_dump() for term in analysis.biased_terms]
            
            stats["biased"] = analysis.is_biased
            
            # Step 2: Debias if biased
            if analysis.is_biased and len(analysis.biased_terms) > 0:
                debiased = await self.bias_detector.debias_article(
                    article.original_content,
                    [term.model_dump() for term in analysis.biased_terms]
                )
                
                article.debiased_content = debiased.debiased_content
                article.changes_made = [change.model_dump() for change in debiased.changes]
                article.total_changes = debiased.total_changes
                
                stats["changes_made"] = debiased.total_changes
                
                # Generate neutral headline
                try:
                    headline = await self.bias_detector.generate_neutral_headline(
                        debiased.debiased_content,
                        article.title
                    )
                    article.generated_headlines = headline.generated_headlines
                    article.recommended_headline = headline.recommended_headline
                except Exception as e:
                    logger.warning(f"Headline generation failed for article {article.id}: {str(e)}")
            
            # Mark as processed
            article.processed = True
            article.processed_at = datetime.utcnow()
            article.processing_error = None
            
            self.db.commit()
            stats["success"] = True
            
            logger.info(
                f"Processed article {article.id}: "
                f"biased={analysis.is_biased}, "
                f"changes={stats['changes_made']}"
            )
        
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(f"Article {article.id} processing error: {error_msg}")
            
            article.processed = True
            article.processed_at = datetime.utcnow()
            article.processing_error = error_msg
            
            self.db.commit()
            
            stats["error"] = error_msg
        
        return stats
    