"""
Enhanced individual article analysis service with optional TOON format.
Provides manual bias analysis for individual articles with existing prompts.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Article
from app.services.bias_detector import BiasDetectorService
from app.services.openai_service import OpenAIService
from app.utils.enhanced_toon_formatter import enhanced_toon_formatter
from app.models.schemas import BiasAnalysisResponse, DebiasResponse, HeadlineResponse

logger = logging.getLogger(__name__)


class ManualArticleAnalyzer:
    """
    Service for manual individual article analysis with optional TOON format.
    Uses existing prompts for compatibility while providing TOON optimization.
    """
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.bias_detector = BiasDetectorService()
        self.openai_service = OpenAIService()
    
    async def analyze_article_manual(
        self,
        article_id: int,
        use_toon_format: bool = False
    ) -> BiasAnalysisResponse:
        """
        Manually analyze a single article for bias with optional TOON format.
        
        Args:
            article_id: Database article ID
            use_toon_format: Whether to use TOON format for LLM efficiency
            
        Returns:
            Bias analysis results
            
        Raises:
            ValueError: If article not found or already processed
        """
        # Get article from database
        article = self.db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise ValueError(f"Article not found: {article_id}")
        
        if article.processed:
            logger.info(f"Article {article_id} already processed, returning existing results")
            return BiasAnalysisResponse(
                is_biased=article.is_biased,
                bias_score=article.bias_score,
                biased_terms=article.biased_terms or [],
                summary=article.bias_summary or "Already analyzed",
                confidence=0.8  # Default confidence for processed articles
            )
        
        logger.info(f"Manual analysis for article {article_id}: '{article.title[:50]}...'")
        
        try:
            if use_toon_format:
                # Use TOON format for efficiency
                result = await self._analyze_with_toon(article)
                logger.info(f"TOON format used - Analysis complete")
            else:
                # Use existing bias detector with original prompts
                result = await self.bias_detector.analyze_bias(
                    article.original_content,
                    article.title
                )
                logger.info(f"Original format used - Analysis complete")
            
            # Update article with analysis results
            article.is_biased = result.is_biased
            article.bias_score = result.bias_score
            article.bias_summary = result.summary
            article.biased_terms = [term.model_dump() for term in result.biased_terms]
            article.processed = True
            article.processed_at = datetime.utcnow()
            article.processing_error = None
            
            self.db.commit()
            
            logger.info(
                f"Manual analysis complete for article {article_id}: "
                f"biased={result.is_biased}, score={result.bias_score}"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Manual analysis failed for article {article_id}: {str(e)}"
            logger.error(error_msg)
            
            # Update article with error
            article.processed = True
            article.processed_at = datetime.utcnow()
            article.processing_error = error_msg
            self.db.commit()
            
            raise ValueError(error_msg)
    
    async def _analyze_with_toon(self, article: Article) -> BiasAnalysisResponse:
        """
        Analyze article using TOON format for LLM efficiency.
        
        Args:
            article: Article database model
            
        Returns:
            Bias analysis results
        """
        # Prepare article data in TOON format
        article_data = {
            "id": str(article.id),
            "title": article.title or "",
            "content": article.original_content[:2000] if len(article.original_content) > 2000 else article.original_content,
            "source": article.source or "",
            "date": article.published_date.isoformat() if article.published_date else ""
        }
        
        # Convert to TOON format
        toon_input = enhanced_toon_formatter.format_single_article_for_bias(article_data)
        
        # Use existing system prompt (for compatibility) with TOON data
        system_prompt = """You are a bias detection expert for Bengali news articles. Analyze the article and respond ONLY with valid JSON.

JSON structure:
{
  "is_biased": boolean,
  "bias_score": number (0-100),
  "biased_terms": [
    {
      "term": "biased word",
      "reason": "explanation",
      "neutral_alternative": "neutral word",
      "severity": "low/medium/high"
    }
  ],
  "summary": "analysis summary",
  "confidence": number (0.0-1.0)
}

Look for: politically charged language, emotional manipulation, sensationalism, one-sided framing."""
        
        user_prompt = f"""Analyze this article for bias:

Article data in TOON format (30-60% token reduction):
```toon
{toon_input}
```

Provide bias analysis in JSON format."""
        
        # Log token savings
        original_chars = len(article.original_content) + len(article.title or "")
        toon_chars = len(toon_input)
        token_savings = max(0, (original_chars - toon_chars) // 4)  # Approximate tokens saved
        
        logger.info(f"TOON format - Original: ~{original_chars//4} tokens, TOON: ~{toon_chars//2} tokens, Saved: {token_savings} tokens")
        
        # Call OpenAI API
        response = await self.openai_service._call_api(
            system_prompt,
            user_prompt,
            "json_object",
            dynamic_max_tokens=False
        )
        
        # Parse response
        json_str = self.openai_service._extract_json(response)
        import json
        parsed_result = json.loads(json_str)
        
        # Convert to BiasAnalysisResponse
        biased_terms = []
        for term_data in parsed_result.get("biased_terms", []):
            biased_terms.append({
                "term": term_data.get("term", ""),
                "reason": term_data.get("reason", ""),
                "neutral_alternative": term_data.get("neutral_alternative", ""),
                "severity": term_data.get("severity", "medium")
            })
        
        return BiasAnalysisResponse(
            is_biased=parsed_result.get("is_biased", False),
            bias_score=float(parsed_result.get("bias_score", 0.0)),
            biased_terms=biased_terms,
            summary=parsed_result.get("summary", "No analysis available"),
            confidence=float(parsed_result.get("confidence", 0.0))
        )
    
    async def debias_article_manual(
        self,
        article_id: int
    ) -> Dict[str, Any]:
        """
        Manually debias a single article (if biased).
        
        Args:
            article_id: Database article ID
            
        Returns:
            Debiasing results
            
        Raises:
            ValueError: If article not found or not analyzed
        """
        # Get article from database
        article = self.db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise ValueError(f"Article not found: {article_id}")
        
        if not article.processed:
            raise ValueError(f"Article {article_id} must be analyzed first")
        
        if not article.is_biased:
            return {
                "status": "success",
                "message": "Article is not biased - no debiasing needed",
                "changes_made": 0,
                "debiased_content": article.original_content
            }
        
        logger.info(f"Manual debiasing for article {article_id}: '{article.title[:50]}...'")
        
        try:
            # Use existing debias functionality
            biased_terms = [term.model_dump() for term in article.biased_terms] if article.biased_terms else None
            
            result = await self.bias_detector.debias_article(
                article.original_content,
                biased_terms
            )
            
            # Update article with debiasing results
            article.debiased_content = result.debiased_content
            article.changes_made = [change.model_dump() for change in result.changes]
            article.total_changes = result.total_changes
            
            # Generate neutral headline
            try:
                headline_result = await self.bias_detector.generate_neutral_headline(
                    result.debiased_content,
                    article.title
                )
                article.generated_headlines = headline_result.generated_headlines
                article.recommended_headline = headline_result.recommended_headline
            except Exception as e:
                logger.warning(f"Headline generation failed for article {article_id}: {str(e)}")
            
            self.db.commit()
            
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
            
        except Exception as e:
            error_msg = f"Manual debiasing failed for article {article_id}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_article_analysis_status(self, article_id: int) -> Dict[str, Any]:
        """
        Get the current analysis status of an article.
        
        Args:
            article_id: Database article ID
            
        Returns:
            Article analysis status
            
        Raises:
            ValueError: If article not found
        """
        article = self.db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise ValueError(f"Article not found: {article_id}")
        
        return {
            "article_id": article.id,
            "title": article.title,
            "source": article.source,
            "processed": article.processed,
            "is_biased": article.is_biased,
            "bias_score": article.bias_score,
            "has_debiased_content": bool(article.debiased_content),
            "has_generated_headlines": bool(article.generated_headlines),
            "processing_error": article.processing_error,
            "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            "ready_for_analysis": not article.processed,
            "ready_for_debiasing": article.processed and article.is_biased and not article.debiased_content
        }