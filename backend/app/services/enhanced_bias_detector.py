"""
Enhanced bias detection service with TOON format optimization and batch processing.
Supports up to 20 articles per LLM analysis call for maximum efficiency.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from app.services.openai_service import OpenAIService
from app.utils.enhanced_toon_formatter import (
    enhanced_toon_formatter, 
    format_articles_for_llm,
    create_bias_detection_prompt
)
from app.models.schemas import (
    BiasAnalysisResponse,
    DebiasResponse,
    HeadlineResponse,
    FullProcessResponse,
    BiasedTerm,
    ContentChange
)
from app.models.enhanced_schemas import BatchBiasAnalysisResponse

logger = logging.getLogger(__name__)


class EnhancedBiasDetectorService:
    """
    Enhanced bias detection service with TOON format optimization.
    Processes up to 20 articles in a single LLM call for maximum efficiency.
    """
    
    def __init__(self):
        """Initialize with OpenAI service and enhanced TOON formatter."""
        self.openai_service = OpenAIService()
        self.max_batch_size = 20  # Maximum articles per LLM analysis
    
    async def analyze_bias_batch(
        self, 
        articles: List[Dict[str, Any]], 
        use_toon_format: bool = True
    ) -> BatchBiasAnalysisResponse:
        """
        Analyze multiple articles for bias in a single LLM call.
        
        Args:
            articles: List of article dictionaries with id, title, content, source
            use_toon_format: Whether to use TOON format for efficiency
            
        Returns:
            Batch bias analysis response with results for all articles
        """
        if not articles:
            return BatchBiasAnalysisResponse(articles=[], total_processed=0)
        
        # Limit to maximum batch size
        articles_to_process = articles[:self.max_batch_size]
        logger.info(f"Analyzing bias for {len(articles_to_process)} articles in batch")
        
        try:
            if use_toon_format:
                # Use TOON format for 30-60% token reduction
                toon_data = format_articles_for_llm(articles_to_process, self.max_batch_size)
                system_prompt, user_prompt = create_bias_detection_prompt(toon_data)
                
                # Log token savings
                original_data = {"articles": articles_to_process}
                savings = enhanced_toon_formatter.calculate_token_savings(original_data, toon_data)
                logger.info(f"TOON format savings: {savings['savings_percent']}% token reduction")
                
            else:
                # Fallback to JSON format
                system_prompt = self._create_json_system_prompt()
                user_prompt = self._create_json_user_prompt(articles_to_process)
                savings = {"savings_percent": 0}
            
            # Make single LLM call for entire batch
            response = await self.openai_service._call_api(
                system_prompt, 
                user_prompt, 
                "json_object",
                dynamic_max_tokens=True
            )
            
            # Parse response
            batch_result = self._parse_batch_response(response, use_toon_format)
            
            # Convert BiasAnalysisResponse objects to dictionaries for Pydantic
            articles_dict = [article.model_dump() if hasattr(article, 'model_dump') else article for article in batch_result]
            
            return BatchBiasAnalysisResponse(
                articles=batch_result,
                total_processed=len(articles_to_process),
                format_used="TOON" if use_toon_format else "JSON",
                token_savings=savings['savings_percent'] if use_toon_format else 0
            )
            
        except Exception as e:
            logger.error(f"Batch bias analysis failed: {str(e)}")
            # Fallback to individual analysis
            return await self._fallback_individual_analysis(articles_to_process)
    
    async def analyze_single_article(
        self, 
        content: str, 
        title: Optional[str] = None,
        article_id: Optional[str] = None,
        use_toon_format: bool = True
    ) -> BiasAnalysisResponse:
        """
        Analyze single article for bias with TOON format optimization.
        
        Args:
            content: Article content
            title: Optional article title
            article_id: Optional article ID
            use_toon_format: Whether to use TOON format
            
        Returns:
            Structured bias analysis response
        """
        try:
            if use_toon_format:
                # Use TOON format for efficiency
                article_data = {
                    "id": article_id or "single",
                    "title": title or "",
                    "content": content[:2000]  # Truncate for efficiency
                }
                
                toon_input = enhanced_toon_formatter.format_single_article_for_bias(article_data)
                
                system_prompt = """You are a bias detection expert. Analyze the article and respond with JSON bias analysis.

Response format:
{
  "is_biased": boolean,
  "bias_score": 0-100,
  "biased_terms": [{"term": "word", "reason": "explanation", "neutral_alternative": "word", "severity": "low/medium/high"}],
  "summary": "analysis summary",
  "confidence": 0.0-1.0
}"""

                user_prompt = f"""Analyze this article for bias:

Article data in TOON format:
```toon
{toon_input}
```

Provide bias analysis in JSON format."""

                response = await self.openai_service._call_api(
                    system_prompt, 
                    user_prompt, 
                    "json_object",
                    dynamic_max_tokens=False
                )
                
                # Parse single article response
                result = self.openai_service._extract_json(response)
                import json
                parsed_result = json.loads(result)
                
            else:
                # Use existing OpenAI service
                parsed_result = await self.openai_service.detect_bias(content, title)
            
            # Convert to Pydantic model
            biased_terms = [
                BiasedTerm(**term) for term in parsed_result.get("biased_terms", [])
            ]
            
            return BiasAnalysisResponse(
                is_biased=parsed_result.get("is_biased", False),
                bias_score=float(parsed_result.get("bias_score", 0.0)),
                biased_terms=biased_terms,
                summary=parsed_result.get("summary", "No analysis available"),
                confidence=float(parsed_result.get("confidence", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Single article bias analysis failed: {str(e)}")
            return BiasAnalysisResponse(
                is_biased=False,
                bias_score=0.0,
                biased_terms=[],
                summary=f"Analysis error: {str(e)}",
                confidence=0.0
            )
    
    def _create_json_system_prompt(self) -> str:
        """Create system prompt for JSON format batch analysis."""
        return """You are a bias detection expert for news articles. Analyze all provided articles and respond with JSON containing bias analysis for each article.

Response format:
{
  "articles": [
    {
      "id": "article_id",
      "is_biased": boolean,
      "bias_score": 0-100,
      "biased_terms": [{"term": "word", "reason": "explanation", "neutral_alternative": "word"}],
      "summary": "analysis summary"
    }
  ]
}"""
    
    def _create_json_user_prompt(self, articles: List[Dict[str, Any]]) -> str:
        """Create user prompt for JSON format batch analysis."""
        articles_data = []
        for article in articles:
            articles_data.append({
                "id": article.get("id", ""),
                "title": article.get("title", "")[:100],
                "content": article.get("content", "")[:500],
                "source": article.get("source", "")
            })
        
        return f"""Analyze these {len(articles)} articles for bias:

Articles data in JSON format:
```json
{{"articles": {articles_data}}}
```

Provide bias analysis in JSON format."""
    
    def _parse_batch_response(self, response: str, use_toon_format: bool) -> List[BiasAnalysisResponse]:
        """Parse batch analysis response from LLM."""
        try:
            import json
            
            # Extract JSON from response
            json_str = self.openai_service._extract_json(response)
            parsed_response = json.loads(json_str)
            
            results = []
            articles_data = parsed_response.get("articles", [])
            
            for article_data in articles_data:
                biased_terms = [
                    BiasedTerm(**term) for term in article_data.get("biased_terms", [])
                ]
                
                result = BiasAnalysisResponse(
                    is_biased=article_data.get("is_biased", False),
                    bias_score=float(article_data.get("bias_score", 0.0)),
                    biased_terms=biased_terms,
                    summary=article_data.get("summary", "No analysis available"),
                    confidence=float(article_data.get("confidence", 0.0))
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse batch response: {str(e)}")
            raise
    
    async def _fallback_individual_analysis(
        self, 
        articles: List[Dict[str, Any]]
    ) -> BatchBiasAnalysisResponse:
        """
        Fallback to individual analysis if batch analysis fails.
        
        Args:
            articles: List of articles to analyze individually
            
        Returns:
            Batch response with individual results
        """
        logger.warning("Falling back to individual article analysis")
        
        results = []
        for article in articles:
            try:
                result = await self.analyze_single_article(
                    content=article.get("content", ""),
                    title=article.get("title", ""),
                    article_id=article.get("id"),
                    use_toon_format=False  # Use JSON for individual analysis
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Individual analysis failed for article {article.get('id')}: {str(e)}")
                # Add error result
                results.append(BiasAnalysisResponse(
                    is_biased=False,
                    bias_score=0.0,
                    biased_terms=[],
                    summary=f"Analysis error: {str(e)}",
                    confidence=0.0
                ))
        
        return BatchBiasAnalysisResponse(
            articles=results,
            total_processed=len(results),
            format_used="JSON (individual)",
            token_savings=0
        )
    
    async def debias_article(
        self,
        content: str,
        biased_terms: Optional[list] = None,
        use_toon_format: bool = True
    ) -> DebiasResponse:
        """
        Enhanced article debiasing with TOON format support.
        
        Args:
            content: Original article content
            biased_terms: Optional list of biased terms (if already analyzed)
            use_toon_format: Whether to use TOON format for efficiency
            
        Returns:
            Debiased content with change tracking
        """
        try:
            # Use existing debiasing service
            result = await self.openai_service.debias_content(content, biased_terms)
            
            # Convert to Pydantic model
            changes = [
                ContentChange(**change) for change in result.get("changes", [])
            ]
            
            return DebiasResponse(
                original_content=content,
                debiased_content=result.get("debiased_content", content),
                changes_made=changes,
                bias_reduction_score=float(result.get("bias_reduction_score", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Enhanced debiasing failed: {str(e)}")
            return DebiasResponse(
                original_content=content,
                debiased_content=content,
                changes_made=[],
                bias_reduction_score=0.0
            )


# Enhanced service singleton
enhanced_bias_detector = EnhancedBiasDetectorService()