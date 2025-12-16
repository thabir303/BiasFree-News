"""
Bias detection orchestration service.
Coordinates OpenAI calls for complete bias analysis pipeline.
"""
import logging
import time
from typing import Optional
from app.services.openai_service import OpenAIService
from app.models.schemas import (
    BiasAnalysisResponse,
    DebiasResponse,
    HeadlineResponse,
    FullProcessResponse,
    BiasedTerm,
    ContentChange
)

logger = logging.getLogger(__name__)


class BiasDetectorService:
    """
    High-level service for bias detection and content processing.
    Orchestrates OpenAI service calls and formats responses.
    """
    
    def __init__(self):
        """Initialize with OpenAI service."""
        self.openai_service = OpenAIService()
    
    async def analyze_bias(self, content: str, title: Optional[str] = None) -> BiasAnalysisResponse:
        """
        Analyze article for bias.
        
        Args:
            content: Article content
            title: Optional article title
        
        Returns:
            Structured bias analysis response
        """
        try:
            result = await self.openai_service.detect_bias(content, title)
            
            # Convert to Pydantic model
            biased_terms = [
                BiasedTerm(**term) for term in result.get("biased_terms", [])
            ]
            
            return BiasAnalysisResponse(
                is_biased=result.get("is_biased", False),
                bias_score=float(result.get("bias_score", 0.0)),
                biased_terms=biased_terms,
                summary=result.get("summary", "No analysis available"),
                confidence=float(result.get("confidence", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Bias analysis failed: {str(e)}")
            # Return safe default response
            return BiasAnalysisResponse(
                is_biased=False,
                bias_score=0.0,
                biased_terms=[],
                summary=f"Analysis error: {str(e)}",
                confidence=0.0
            )
    
    async def debias_article(
        self,
        content: str,
        biased_terms: Optional[list] = None
    ) -> DebiasResponse:
        """
        Debias article content.
        
        Args:
            content: Original article content
            biased_terms: Optional list of biased terms (if already analyzed)
        
        Returns:
            Debiased content with change tracking
        """
        try:
            # If biased terms not provided, detect them first
            if biased_terms is None:
                analysis = await self.analyze_bias(content)
                biased_terms = [term.model_dump() for term in analysis.biased_terms]
            
            # Perform debiasing
            result = await self.openai_service.debias_content(content, biased_terms)
            
            # Convert to Pydantic model
            changes = [
                ContentChange(**change) for change in result.get("changes", [])
            ]
            
            return DebiasResponse(
                original_content=content,
                debiased_content=result.get("debiased_content", content),
                changes=changes,
                total_changes=len(changes)
            )
            
        except Exception as e:
            logger.error(f"Debiasing failed: {str(e)}")
            return DebiasResponse(
                original_content=content,
                debiased_content=content,
                changes=[],
                total_changes=0
            )
    
    async def generate_neutral_headline(
        self,
        content: str,
        original_title: Optional[str] = None
    ) -> HeadlineResponse:
        """
        Generate neutral headline for article.
        
        Args:
            content: Article content
            original_title: Original headline
        
        Returns:
            Generated headlines with recommendation
        """
        try:
            result = await self.openai_service.generate_headline(content, original_title)
            
            # Ensure we have at least one headline
            headlines = result.get("generated_headlines", [])
            if not headlines:
                fallback = original_title if original_title else "নিরপেক্ষ শিরোনাম"
                headlines = [fallback]
            
            recommended = result.get("recommended_headline", "")
            if not recommended:
                recommended = headlines[0]
            
            return HeadlineResponse(
                original_title=original_title,
                generated_headlines=headlines,
                recommended_headline=recommended,
                reasoning=result.get("reasoning", "Auto-generated")
            )
            
        except Exception as e:
            logger.error(f"Headline generation failed: {str(e)}")
            fallback = original_title if original_title else "শিরোনাম তৈরি করা সম্ভব হয়নি"
            return HeadlineResponse(
                original_title=original_title,
                generated_headlines=[fallback],
                recommended_headline=fallback,
                reasoning=f"Error: {str(e)}"
            )
    
    async def full_process(
        self,
        content: str,
        title: Optional[str] = None
    ) -> FullProcessResponse:
        """
        Complete bias-free processing pipeline.
        Analyzes, debiases, and generates headline in one call.
        
        Args:
            content: Article content
            title: Original article title
        
        Returns:
            Complete processing results
        """
        start_time = time.time()
        
        try:
            # Step 1: Analyze bias
            analysis = await self.analyze_bias(content, title)
            
            # Step 2: Debias content (reuse biased terms from analysis)
            biased_terms = [term.model_dump() for term in analysis.biased_terms]
            debiased = await self.debias_article(content, biased_terms)
            
            # Step 3: Generate neutral headline
            headline = await self.generate_neutral_headline(
                debiased.debiased_content,
                title
            )
            
            processing_time = time.time() - start_time
            
            return FullProcessResponse(
                analysis=analysis,
                debiased=debiased,
                headline=headline,
                processing_time_seconds=round(processing_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Full processing failed: {str(e)}")
            raise
