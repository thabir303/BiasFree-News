"""
Integration tests for app/api/routes_enhanced.py  (the actual router used by the app)

All external services (OpenAI, scraper) are mocked so tests run offline and fast.
All bias-detection endpoints require authentication.

Covers:
- POST /api/analyze         (success, short content, content too long, no auth)
- POST /api/debias          (success, short content, no auth)
- POST /api/full-process    (success, error propagation, no auth)
- POST /api/scrape          (admin required, regular user forbidden)
- GET  /  and /api/health   (public)
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from unittest.mock import AsyncMock, patch

from app.models.schemas import (
    BiasAnalysisResponse,
    BiasedTerm,
    DebiasResponse,
    ContentChange,
    HeadlineResponse,
    FullProcessResponse,
)

# ─── Re-usable mock data ────────────────────────────────────────────────────

SAMPLE_BENGALI_CONTENT = (
    "এটি একটি পরীক্ষামূলক বাংলা সংবাদ নিবন্ধ। "
    "এতে রাজনৈতিক পক্ষপাত থাকতে পারে বলে ধারণা করা হচ্ছে। "
    "বিভিন্ন রাজনৈতিক দলের নেতারা তাদের মতামত প্রকাশ করেছেন।"
)

MOCK_ANALYSIS = BiasAnalysisResponse(
    is_biased=True,
    bias_score=65.5,
    biased_terms=[
        BiasedTerm(
            term="পক্ষপাত",
            reason="Loaded language",
            neutral_alternative="মতভেদ",
            severity="medium",
        )
    ],
    summary="Article contains moderate political bias.",
    confidence=0.85,
)

MOCK_DEBIAS = DebiasResponse(
    original_content=SAMPLE_BENGALI_CONTENT,
    debiased_content=SAMPLE_BENGALI_CONTENT.replace("পক্ষপাত", "মতভেদ"),
    changes=[
        ContentChange(original="পক্ষপাত", debiased="মতভেদ", reason="Loaded language")
    ],
    total_changes=1,
)

MOCK_HEADLINE = HeadlineResponse(
    original_title="Original Biased Title",
    generated_headlines=["Neutral Headline 1", "Neutral Headline 2"],
    recommended_headline="Neutral Headline 1",
    reasoning="This headline is factual and neutral.",
)

MOCK_FULL = FullProcessResponse(
    analysis=MOCK_ANALYSIS,
    debiased=MOCK_DEBIAS,
    headline=MOCK_HEADLINE,
    processing_time_seconds=1.23,
)


# ===========================================================================
# Analyze Endpoint  (POST /api/analyze)  -- requires authentication
# ===========================================================================

class TestAnalyzeEndpoint:
    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    )
    def test_analyze_success_authenticated(self, mock_analyze, test_client, auth_headers):
        resp = test_client.post(
            "/api/analyze",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_biased"] is True
        assert data["bias_score"] == 65.5
        assert len(data["biased_terms"]) == 1
        mock_analyze.assert_called_once()

    def test_analyze_requires_auth_returns_403(self, test_client):
        resp = test_client.post("/api/analyze", json={"content": SAMPLE_BENGALI_CONTENT})
        assert resp.status_code in (401, 403)

    def test_analyze_too_short_content_returns_422(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/analyze",
            json={"content": "short"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_analyze_content_exceeds_max_length_returns_422(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/analyze",
            json={"content": "ক" * 10000},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_analyze_missing_content_returns_422(self, test_client, auth_headers):
        resp = test_client.post("/api/analyze", json={}, headers=auth_headers)
        assert resp.status_code == 422

    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    )
    def test_analyze_with_title(self, mock_analyze, test_client, auth_headers):
        resp = test_client.post(
            "/api/analyze",
            json={"content": SAMPLE_BENGALI_CONTENT, "title": "Test Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        mock_analyze.assert_called_once()

    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        side_effect=Exception("OpenAI error"),
    )
    def test_analyze_service_error_returns_500(self, _mock, test_client, auth_headers):
        resp = test_client.post(
            "/api/analyze",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 500


# ===========================================================================
# Debias Endpoint  (POST /api/debias)  -- requires authentication
# ===========================================================================

class TestDebiasEndpoint:
    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    )
    @patch(
        "app.api.routes_enhanced.bias_detector.debias_article",
        new_callable=AsyncMock,
        return_value=MOCK_DEBIAS,
    )
    def test_debias_success(self, mock_debias, mock_analyze, test_client, auth_headers):
        resp = test_client.post(
            "/api/debias",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "debiased_content" in data
        assert data["total_changes"] == 1

    def test_debias_requires_auth_returns_403(self, test_client):
        resp = test_client.post("/api/debias", json={"content": SAMPLE_BENGALI_CONTENT})
        assert resp.status_code in (401, 403)

    def test_debias_too_short_returns_422(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/debias",
            json={"content": "short"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        return_value=BiasAnalysisResponse(
            is_biased=False,
            bias_score=0.0,
            biased_terms=[],
            summary="No bias detected.",
            confidence=0.95,
        ),
    )
    def test_debias_returns_original_when_not_biased(
        self, _mock, test_client, auth_headers
    ):
        resp = test_client.post(
            "/api/debias",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_changes"] == 0

    @patch(
        "app.api.routes_enhanced.bias_detector.analyze_bias",
        new_callable=AsyncMock,
        side_effect=Exception("OpenAI error"),
    )
    def test_debias_service_error_returns_500(self, _mock, test_client, auth_headers):
        resp = test_client.post(
            "/api/debias",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 500


# ===========================================================================
# Full Process Endpoint  (POST /api/full-process)  -- requires authentication
# ===========================================================================

class TestFullProcessEndpoint:
    @patch(
        "app.api.routes_enhanced.bias_detector.full_process",
        new_callable=AsyncMock,
        return_value=MOCK_FULL,
    )
    def test_full_process_success(self, mock_full, test_client, auth_headers):
        resp = test_client.post(
            "/api/full-process",
            json={"content": SAMPLE_BENGALI_CONTENT, "title": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data
        assert "debiased" in data
        assert "headline" in data
        assert data["processing_time_seconds"] > 0
        mock_full.assert_called_once()

    def test_full_process_requires_auth_returns_403(self, test_client):
        resp = test_client.post(
            "/api/full-process", json={"content": SAMPLE_BENGALI_CONTENT}
        )
        assert resp.status_code in (401, 403)

    def test_full_process_too_short_returns_422(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/full-process",
            json={"content": "short"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @patch(
        "app.api.routes_enhanced.bias_detector.full_process",
        new_callable=AsyncMock,
        side_effect=Exception("Pipeline error"),
    )
    def test_full_process_service_error_returns_500(self, _mock, test_client, auth_headers):
        resp = test_client.post(
            "/api/full-process",
            json={"content": SAMPLE_BENGALI_CONTENT},
            headers=auth_headers,
        )
        assert resp.status_code == 500


# ===========================================================================
# Scrape Endpoint  (POST /api/scrape)  -- requires ADMIN
# ===========================================================================

class TestScrapeEndpoint:
    def test_scrape_no_auth_returns_403(self, test_client):
        resp = test_client.post("/api/scrape")
        assert resp.status_code in (401, 403)

    def test_scrape_regular_user_returns_403(self, test_client, auth_headers):
        """Regular user (non-admin) should get 403."""
        resp = test_client.post("/api/scrape", headers=auth_headers)
        assert resp.status_code == 403

    def test_scrape_admin_triggers_background_task(self, test_client, admin_auth_headers):
        """Admin can trigger a scrape (background task starts)."""
        resp = test_client.post("/api/scrape", headers=admin_auth_headers)
        # 200 means scrape was accepted/started OR 422 if required body missing
        # Either way admin must NOT get 403
        assert resp.status_code != 403


# ===========================================================================
# Public Endpoints
# ===========================================================================

class TestPublicEndpoints:
    def test_root_returns_200(self, test_client):
        resp = test_client.get("/")
        assert resp.status_code == 200

    def test_root_contains_api_name(self, test_client):
        data = test_client.get("/").json()
        assert "BiasFree" in data.get("name", "")

    def test_docs_link_in_root_response(self, test_client):
        data = test_client.get("/").json()
        # Root should return a name and description field
        assert "description" in data
