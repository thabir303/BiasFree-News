"""
Enhanced article processing service with TOON format optimization and batch processing.
Processes up to 20 articles per LLM call for maximum efficiency.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.models import Article
from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
from app.services.bias_detector import BiasDetectorService  # Fallback
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Configuration constants
MAX_ARTICLES_PER_BATCH = 20  # Maximum articles for single LLM analysis
LLM_DELAY_SECONDS = 2  # Delay between LLM calls for rate limiting


class EnhancedArticleProcessor:
    """
    Enhanced article processing service with batch bias detection.
    Uses TOON format for 30-60% token reduction and processes up to 20 articles per LLM call.
    """
    
    def __init__(self, db: Session):
        """Initialize with database session and enhanced services."""
        self.db = db
        self.enhanced_bias_detector = EnhancedBiasDetectorService()
        self.fallback_bias_detector = BiasDetectorService()  # Fallback for single articles
        self.openai_service = OpenAIService()
    
    async def process_article_single(self, article: Article, use_enhanced: bool = True) -> Dict[str, Any]:
        """
        Process a single article: detect bias and debias if needed.
        
        Args:
            article: Article database model
            use_enhanced: Whether to use enhanced TOON-based detection
            
        Returns:
            Processing statistics
        """
        stats = {
            "article_id": article.id,
            "success": False,
            "biased": False,
            "changes_made": 0,
            "error": None,
            "format_used": "TOON" if use_enhanced else "JSON"
        }
        
        try:
            # Step 1: Analyze for bias
            if use_enhanced:
                # Use enhanced TOON-based detection
                analysis = await self.enhanced_bias_detector.analyze_single_article(
                    content=article.original_content,
                    title=article.title,
                    article_id=str(article.id),
                    use_toon_format=True
                )
            else:
                # Use fallback JSON-based detection
                analysis = await self.fallback_bias_detector.analyze_bias(
                    article.original_content,
                    article.title
                )
            
            # Update article with analysis results
            article.is_biased = analysis.is_biased
            article.bias_score = analysis.bias_score
            article.bias_summary = analysis.summary
            article.biased_terms = [term.model_dump() for term in analysis.biased_terms]
            
            stats["biased"] = analysis.is_biased
            stats["format_used"] = "TOON" if use_enhanced else "JSON"
            
            # Step 2: Debias if biased
            if analysis.is_biased and len(analysis.biased_terms) > 0:
                if use_enhanced:
                    debiased = await self.enhanced_bias_detector.debias_article(
                        article.original_content,
                        [term.model_dump() for term in analysis.biased_terms],
                        use_toon_format=True
                    )
                else:
                    debiased = await self.fallback_bias_detector.debias_article(
                        article.original_content,
                        [term.model_dump() for term in analysis.biased_terms]
                    )
                
                article.debiased_content = debiased.debiased_content
                article.changes_made = [change.model_dump() for change in debiased.changes]
                article.total_changes = debiased.total_changes
                
                stats["changes_made"] = debiased.total_changes
                
                # Generate neutral headline
                try:
                    headline = await self.fallback_bias_detector.generate_neutral_headline(
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
                f"changes={stats['changes_made']}, "
                f"format={stats['format_used']}"
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
    
    async def process_articles_batch(self, articles: List[Article]) -> Dict[str, Any]:
        """
        Process multiple articles in a single batch using TOON format for efficiency.
        
        Args:
            articles: List of Article database models (max 20)
            
        Returns:
            Batch processing statistics
        """
        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "biased_found": 0,
            "total_changes": 0,
            "format_used": "TOON",
            "token_savings": 0,
            "batch_size": len(articles)
        }
        
        if not articles:
            return stats
        
        # Limit to maximum batch size
        articles_to_process = articles[:MAX_ARTICLES_PER_BATCH]
        logger.info(f"Processing batch of {len(articles_to_process)} articles with TOON format")
        
        try:
            # Convert articles to format suitable for batch analysis
            batch_articles = []
            for article in articles_to_process:
                batch_articles.append({
                    "id": str(article.id),
                    "title": article.title or "",
                    "content": article.original_content or "",
                    "source": article.source or "",
                    "date": article.published_date.isoformat() if article.published_date else ""
                })
            
            # Perform batch bias analysis using enhanced service
            batch_result = await self.enhanced_bias_detector.analyze_bias_batch(
                articles=batch_articles,
                use_toon_format=True
            )
            
            # Process individual articles based on batch results
            for idx, (article, analysis) in enumerate(zip(articles_to_process, batch_result.articles)):
                try:
                    # Update article with analysis results
                    article.is_biased = analysis.is_biased
                    article.bias_score = analysis.bias_score
                    article.bias_summary = analysis.summary
                    article.biased_terms = [term.model_dump() for term in analysis.biased_terms]
                    
                    stats["total_processed"] += 1
                    
                    if analysis.is_biased:
                        stats["biased_found"] += 1
                        
                        # Debias the article
                        debiased = await self.enhanced_bias_detector.debias_article(
                            article.original_content,
                            [term.model_dump() for term in analysis.biased_terms],
                            use_toon_format=True
                        )
                        
                        article.debiased_content = debiased.debiased_content
                        article.changes_made = [change.model_dump() for change in debiased.changes]
                        article.total_changes = debiased.total_changes
                        
                        stats["total_changes"] += debiased.total_changes
                        
                        # Generate neutral headline
                        try:
                            headline = await self.fallback_bias_detector.generate_neutral_headline(
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
                    
                    stats["successful"] += 1
                    
                    logger.info(
                        f"Batch processed article {article.id}: "
                        f"biased={analysis.is_biased}, "
                        f"score={analysis.bias_score}"
                    )
                    
                except Exception as e:
                    error_msg = f"Batch processing failed for article {article.id}: {str(e)}"
                    logger.error(error_msg)
                    
                    article.processed = True
                    article.processed_at = datetime.utcnow()
                    article.processing_error = error_msg
                    
                    stats["failed"] += 1
            
            # Store token savings from TOON format
            stats["token_savings"] = batch_result.token_savings
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"Batch processing complete: "
                f"{stats['successful']} successful, "
                f"{stats['failed']} failed, "
                f"{stats['biased_found']} biased articles found, "
                f"{stats['token_savings']}% token savings"
            )
            
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            # Fallback to individual processing
            return await self._fallback_to_individual_processing(articles_to_process)
        
        return stats
    
    async def process_unprocessed_articles(self, limit: int = 50) -> Dict[str, Any]:
        """
        Process unprocessed articles from database with batch optimization.
        
        Args:
            limit: Maximum number of articles to process
            
        Returns:
            Processing statistics with batch optimization metrics
        """
        overall_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "biased_found": 0,
            "total_changes": 0,
            "batches_processed": 0,
            "token_savings_total": 0,
            "format_used": "Mixed (TOON + Batch)"
        }
        
        try:
            # Get unprocessed articles
            unprocessed = self.db.query(Article).filter(
                Article.processed == False
            ).limit(limit).all()
            
            logger.info(f"Found {len(unprocessed)} unprocessed articles")
            
            if not unprocessed:
                return overall_stats
            
            # Process in batches of MAX_ARTICLES_PER_BATCH
            batch_size = MAX_ARTICLES_PER_BATCH
            total_batches = (len(unprocessed) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(unprocessed))
                batch_articles = unprocessed[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} with {len(batch_articles)} articles")
                
                # Process batch
                batch_stats = await self.process_articles_batch(batch_articles)
                
                # Update overall statistics
                overall_stats["total_processed"] += batch_stats["total_processed"]
                overall_stats["successful"] += batch_stats["successful"]
                overall_stats["failed"] += batch_stats["failed"]
                overall_stats["biased_found"] += batch_stats["biased_found"]
                overall_stats["total_changes"] += batch_stats["total_changes"]
                overall_stats["batches_processed"] += 1
                overall_stats["token_savings_total"] += batch_stats.get("token_savings", 0)
                
                # Add delay between batches to respect rate limits
                if batch_idx < total_batches - 1:
                    logger.debug(f"Waiting {LLM_DELAY_SECONDS}s before next batch (rate limit)")
                    await asyncio.sleep(LLM_DELAY_SECONDS)
            
            # Calculate average token savings
            if overall_stats["batches_processed"] > 0:
                overall_stats["token_savings_avg"] = overall_stats["token_savings_total"] / overall_stats["batches_processed"]
            
            logger.info(
                f"Enhanced processing complete: "
                f"{overall_stats['total_processed']} total processed, "
                f"{overall_stats['successful']} successful, "
                f"{overall_stats['failed']} failed, "
                f"{overall_stats['biased_found']} biased articles found, "
                f"{overall_stats['batches_processed']} batches processed"
            )
            
        except Exception as e:
            logger.error(f"Enhanced batch processing error: {str(e)}")
            # Fallback to traditional processing
            return await self._fallback_to_traditional_processing(limit)
        
        return overall_stats
    
    async def _fallback_to_individual_processing(self, articles: List[Article]) -> Dict[str, Any]:
        """Fallback to individual processing if batch processing fails."""
        logger.warning("Falling back to individual article processing")
        
        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "biased_found": 0,
            "total_changes": 0,
            "format_used": "JSON (individual fallback)"
        }
        
        for idx, article in enumerate(articles):
            try:
                article_stats = await self.process_article_single(article, use_enhanced=False)
                
                stats["total_processed"] += 1
                
                if article_stats["success"]:
                    stats["successful"] += 1
                    if article_stats["biased"]:
                        stats["biased_found"] += 1
                    stats["total_changes"] += article_stats["changes_made"]
                else:
                    stats["failed"] += 1
                
                # Add delay between LLM calls
                if idx < len(articles) - 1:
                    await asyncio.sleep(LLM_DELAY_SECONDS)
                    
            except Exception as e:
                logger.error(f"Individual processing failed for article {article.id}: {str(e)}")
                stats["failed"] += 1
        
        return stats
    
    async def _fallback_to_traditional_processing(self, limit: int) -> Dict[str, Any]:
        """Fallback to traditional article processor."""
        logger.warning("Falling back to traditional article processor")
        
        # Import and use traditional processor
        from app.services.article_processor import ArticleProcessor
        traditional_processor = ArticleProcessor(self.db)
        
        return await traditional_processor.process_unprocessed_articles(limit)