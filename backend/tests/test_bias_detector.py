"""
Unit tests for app/services/bias_detector.py

All OpenAI service calls are mocked so no real API calls are made.

Covers:
- BiasDetectorService.analyze_bias        : success, error fallback
- BiasDetectorService.debias_article      : success, with/without biased_terms, error fallback
- BiasDetectorService.generate_neutral_headline : success, empty headlines, error fallback
- BiasDetectorService.full_process        : end-to-end pipeline, step ordering, error re-raise
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.bias_detector import BiasDetectorService
from app.models.schemas import (
    BiasAnalysisResponse,
    BiasedTerm,
    DebiasResponse,
    HeadlineResponse,
    FullProcessResponse,
    ContentChange,
)

CONTENT = (
    "এটি একটি পরীক্ষামূলক সংবাদ নিবন্ধ। "
    "এতে রাজনৈতিক পক্ষপাত আছে বলে মনে করা হচ্ছে।"
)


# ===========================================================================
# Shared mock return values
# ===========================================================================

DETECT_BIAS_RESULT = {
    "is_biased": True,
    "bias_score": 72.0,
    "biased_terms": [
        {
            "term": "পক্ষপাত",
            "reason": "Loaded language",
            "neutral_alternative": "মতভেদ",
            "severity": "medium",
        }
    ],
    "summary": "Article contains moderate bias.",
    "confidence": 0.80,
}

DEBIAS_RESULT = {
    "debiased_content": CONTENT.replace("পক্ষপাত", "মতভেদ"),
    "changes": [
        {
            "original": "পক্ষপাত",
            "debiased": "মতভেদ",
            "reason": "Loaded language",
        }
    ],
}

HEADLINE_RESULT = {
    "generated_headlines": ["নিরপেক্ষ শিরোনাম ১", "নিরপেক্ষ শিরোনাম ২"],
    "recommended_headline": "নিরপেক্ষ শিরোনাম ১",
    "reasoning": "Factual and neutral phrasing.",
}


# ===========================================================================
# analyze_bias
# ===========================================================================

class TestAnalyzeBias:
    @pytest.fixture(autouse=True)
    def detector(self):
        self.svc = BiasDetectorService()

    @pytest.mark.asyncio
    async def test_returns_bias_analysis_response(self):
        self.svc.openai_service.detect_bias = AsyncMock(return_value=DETECT_BIAS_RESULT)

        result = await self.svc.analyze_bias(CONTENT)

        assert isinstance(result, BiasAnalysisResponse)
        assert result.is_biased is True
        assert result.bias_score == 72.0
        assert len(result.biased_terms) == 1
        assert result.biased_terms[0].term == "পক্ষপাত"

    @pytest.mark.asyncio
    async def test_passes_title_to_openai(self):
        self.svc.openai_service.detect_bias = AsyncMock(return_value=DETECT_BIAS_RESULT)

        await self.svc.analyze_bias(CONTENT, title="Test Title")

        self.svc.openai_service.detect_bias.assert_called_once_with(CONTENT, "Test Title")

    @pytest.mark.asyncio
    async def test_openai_error_returns_safe_fallback(self):
        self.svc.openai_service.detect_bias = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await self.svc.analyze_bias(CONTENT)

        assert isinstance(result, BiasAnalysisResponse)
        assert result.is_biased is False
        assert result.bias_score == 0.0
        assert result.biased_terms == []
        assert "API error" in result.summary

    @pytest.mark.asyncio
    async def test_zero_confidence_in_error_response(self):
        self.svc.openai_service.detect_bias = AsyncMock(side_effect=Exception("fail"))
        result = await self.svc.analyze_bias(CONTENT)
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_empty_biased_terms_when_not_biased(self):
        self.svc.openai_service.detect_bias = AsyncMock(
            return_value={
                "is_biased": False,
                "bias_score": 0.0,
                "biased_terms": [],
                "summary": "No bias.",
                "confidence": 0.95,
            }
        )
        result = await self.svc.analyze_bias(CONTENT)
        assert result.biased_terms == []


# ===========================================================================
# debias_article
# ===========================================================================

class TestDebiasArticle:
    @pytest.fixture(autouse=True)
    def detector(self):
        self.svc = BiasDetectorService()

    @pytest.mark.asyncio
    async def test_returns_debias_response(self):
        self.svc.openai_service.debias_content = AsyncMock(return_value=DEBIAS_RESULT)

        biased_terms = [{"term": "পক্ষপাত", "reason": "Loaded", "neutral_alternative": "মতভেদ", "severity": "medium"}]
        result = await self.svc.debias_article(CONTENT, biased_terms)

        assert isinstance(result, DebiasResponse)
        assert result.original_content == CONTENT
        assert "মতভেদ" in result.debiased_content
        assert result.total_changes == 1

    @pytest.mark.asyncio
    async def test_auto_detects_terms_when_none_given(self):
        self.svc.openai_service.detect_bias = AsyncMock(return_value=DETECT_BIAS_RESULT)
        self.svc.openai_service.debias_content = AsyncMock(return_value=DEBIAS_RESULT)

        result = await self.svc.debias_article(CONTENT, biased_terms=None)

        # detect_bias was called to fill in the terms automatically
        self.svc.openai_service.detect_bias.assert_called_once()
        assert result.total_changes == 1

    @pytest.mark.asyncio
    async def test_error_returns_original_content(self):
        self.svc.openai_service.debias_content = AsyncMock(
            side_effect=Exception("Debias fail")
        )
        result = await self.svc.debias_article(CONTENT, biased_terms=[])

        assert result.original_content == CONTENT
        assert result.debiased_content == CONTENT
        assert result.total_changes == 0

    @pytest.mark.asyncio
    async def test_no_changes_when_no_biased_terms_in_response(self):
        self.svc.openai_service.debias_content = AsyncMock(
            return_value={"debiased_content": CONTENT, "changes": []}
        )
        result = await self.svc.debias_article(CONTENT, biased_terms=[])
        assert result.changes == []
        assert result.total_changes == 0


# ===========================================================================
# generate_neutral_headline
# ===========================================================================

class TestGenerateNeutralHeadline:
    @pytest.fixture(autouse=True)
    def detector(self):
        self.svc = BiasDetectorService()

    @pytest.mark.asyncio
    async def test_returns_headline_response(self):
        self.svc.openai_service.generate_headline = AsyncMock(
            return_value=HEADLINE_RESULT
        )
        result = await self.svc.generate_neutral_headline(CONTENT, "Original")

        assert isinstance(result, HeadlineResponse)
        assert result.recommended_headline == "নিরপেক্ষ শিরোনাম ১"
        assert len(result.generated_headlines) == 2

    @pytest.mark.asyncio
    async def test_falls_back_to_first_headline_if_no_recommended(self):
        self.svc.openai_service.generate_headline = AsyncMock(
            return_value={
                "generated_headlines": ["Headline A"],
                "recommended_headline": "",
                "reasoning": "test",
            }
        )
        result = await self.svc.generate_neutral_headline(CONTENT)
        assert result.recommended_headline == "Headline A"

    @pytest.mark.asyncio
    async def test_uses_original_title_as_fallback_when_headlines_empty(self):
        self.svc.openai_service.generate_headline = AsyncMock(
            return_value={"generated_headlines": [], "recommended_headline": "", "reasoning": ""}
        )
        result = await self.svc.generate_neutral_headline(CONTENT, "My Title")
        assert "My Title" in result.generated_headlines
        assert result.recommended_headline == "My Title"

    @pytest.mark.asyncio
    async def test_uses_default_bengali_fallback_when_no_title(self):
        self.svc.openai_service.generate_headline = AsyncMock(
            return_value={"generated_headlines": [], "recommended_headline": "", "reasoning": ""}
        )
        result = await self.svc.generate_neutral_headline(CONTENT, None)
        assert result.recommended_headline == "নিরপেক্ষ শিরোনাম"

    @pytest.mark.asyncio
    async def test_error_returns_fallback_response(self):
        self.svc.openai_service.generate_headline = AsyncMock(
            side_effect=Exception("headline error")
        )
        result = await self.svc.generate_neutral_headline(CONTENT, "My Title")
        assert "My Title" in result.recommended_headline
        assert "Error" in result.reasoning or "error" in result.reasoning.lower()


# ===========================================================================
# full_process (end-to-end pipeline)
# ===========================================================================

class TestFullProcess:
    @pytest.fixture(autouse=True)
    def detector(self):
        self.svc = BiasDetectorService()

    @pytest.mark.asyncio
    async def test_full_process_returns_full_process_response(self):
        analysis = BiasAnalysisResponse(
            is_biased=True, bias_score=70.0,
            biased_terms=[BiasedTerm(term="t", reason="r", neutral_alternative="n", severity="low")],
            summary="bias", confidence=0.8,
        )
        debiased = DebiasResponse(
            original_content=CONTENT, debiased_content=CONTENT,
            changes=[], total_changes=0,
        )
        headline = HeadlineResponse(
            original_title="T", generated_headlines=["H"],
            recommended_headline="H", reasoning="ok",
        )

        self.svc.analyze_bias = AsyncMock(return_value=analysis)
        self.svc.debias_article = AsyncMock(return_value=debiased)
        self.svc.generate_neutral_headline = AsyncMock(return_value=headline)

        result = await self.svc.full_process(CONTENT, "Title")

        assert isinstance(result, FullProcessResponse)
        assert result.analysis is analysis
        assert result.debiased is debiased
        assert result.headline is headline
        assert result.processing_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_full_process_calls_steps_in_order(self):
        call_order = []

        async def mock_analyze(*_):
            call_order.append("analyze")
            return BiasAnalysisResponse(
                is_biased=False, bias_score=0, biased_terms=[],
                summary="ok", confidence=1.0,
            )

        async def mock_debias(*_):
            call_order.append("debias")
            return DebiasResponse(
                original_content=CONTENT, debiased_content=CONTENT,
                changes=[], total_changes=0,
            )

        async def mock_headline(*_):
            call_order.append("headline")
            return HeadlineResponse(
                original_title="T", generated_headlines=["H"],
                recommended_headline="H", reasoning="ok",
            )

        self.svc.analyze_bias = mock_analyze
        self.svc.debias_article = mock_debias
        self.svc.generate_neutral_headline = mock_headline

        await self.svc.full_process(CONTENT)
        assert call_order == ["analyze", "debias", "headline"]

    @pytest.mark.asyncio
    async def test_full_process_reraises_exceptions(self):
        self.svc.analyze_bias = AsyncMock(side_effect=Exception("pipeline crash"))

        with pytest.raises(Exception, match="pipeline crash"):
            await self.svc.full_process(CONTENT)

    @pytest.mark.asyncio
    async def test_processing_time_is_non_negative(self):
        analysis = BiasAnalysisResponse(
            is_biased=False, bias_score=0, biased_terms=[],
            summary="ok", confidence=1.0,
        )
        debiased = DebiasResponse(
            original_content=CONTENT, debiased_content=CONTENT,
            changes=[], total_changes=0,
        )
        headline = HeadlineResponse(
            original_title=None, generated_headlines=["H"],
            recommended_headline="H", reasoning="ok",
        )
        self.svc.analyze_bias = AsyncMock(return_value=analysis)
        self.svc.debias_article = AsyncMock(return_value=debiased)
        self.svc.generate_neutral_headline = AsyncMock(return_value=headline)

        result = await self.svc.full_process(CONTENT)
        assert result.processing_time_seconds >= 0
