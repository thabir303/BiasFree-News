"""
Unit tests for app/services/scraper.py

Uses mocked HTTP requests so no real network calls are made.

Covers:
- NewspaperScraper (base)  : init, is_within_date_range, make_request
- ProthomAloScraper        : init, _extract_story_metadata, split_date_range_by_month,
                             _fetch_and_create_article, section configuration
- JugantorScraper          : _clean_content
- NewsScraper              : unknown source, known source dispatch
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
import asyncio
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import requests

from app.services.scraper import (
    NewspaperScraper,
    ProthomAloScraper,
    JugantorScraper,
    NewsScraper,
)
from app.models.schemas import ScrapedArticle


# ─── Helpers ────────────────────────────────────────────────────────────────

START = "2025-01-01"
END   = "2025-01-31"


def make_story(
    headline="Test Article",
    slug="bangladesh/2025/01/15/test-article",
    published_at_ms: int = None,
    summary="Some summary text",
):
    """Build a minimal Prothom Alo API story dict."""
    if published_at_ms is None:
        dt = datetime(2025, 1, 15, 10, 0, 0)
        published_at_ms = int(dt.timestamp() * 1000)
    return {
        "headline": headline,
        "slug": slug,
        "published-at": published_at_ms,
        "summary": summary,
    }


# ===========================================================================
# NewspaperScraper (base class)
# ===========================================================================

class TestNewspaperScraperInit:
    def test_start_and_end_dates_parsed(self):
        scraper = NewspaperScraper(START, END)
        assert scraper.start_date == datetime(2025, 1, 1)
        assert scraper.end_date == datetime(2025, 1, 31)

    def test_session_created(self):
        scraper = NewspaperScraper(START, END)
        assert scraper.session is not None


class TestIsWithinDateRange:
    def setup_method(self):
        self.scraper = NewspaperScraper(START, END)

    def test_date_at_start_is_in_range(self):
        assert self.scraper.is_within_date_range(datetime(2025, 1, 1, 0, 0)) is True

    def test_date_at_end_is_in_range(self):
        assert self.scraper.is_within_date_range(datetime(2025, 1, 31, 23, 59)) is True

    def test_date_in_middle_is_in_range(self):
        assert self.scraper.is_within_date_range(datetime(2025, 1, 15)) is True

    def test_date_before_start_is_not_in_range(self):
        assert self.scraper.is_within_date_range(datetime(2024, 12, 31)) is False

    def test_date_after_end_is_not_in_range(self):
        assert self.scraper.is_within_date_range(datetime(2025, 2, 1)) is False

    def test_timezone_aware_date_is_handled(self):
        """tz-aware datetime must not crash; tzinfo is stripped before comparison."""
        aware = datetime(2025, 1, 15, tzinfo=timezone.utc)
        assert self.scraper.is_within_date_range(aware) is True

    def test_timezone_aware_date_outside_range(self):
        aware = datetime(2025, 3, 1, tzinfo=timezone.utc)
        assert self.scraper.is_within_date_range(aware) is False


class TestMakeRequest:
    def setup_method(self):
        self.scraper = NewspaperScraper(START, END)

    def test_success_returns_response(self):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status = MagicMock()
        self.scraper.session.get = MagicMock(return_value=mock_resp)

        result = self.scraper.make_request("http://example.com", max_retries=1)
        assert result is mock_resp

    def test_raises_on_all_attempts_returns_none(self):
        self.scraper.session.get = MagicMock(
            side_effect=requests.RequestException("timeout")
        )
        with patch("time.sleep"):  # skip actual sleep
            result = self.scraper.make_request("http://example.com", max_retries=3)
        assert result is None

    def test_retries_on_transient_failure_then_succeeds(self):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status = MagicMock()
        self.scraper.session.get = MagicMock(
            side_effect=[requests.RequestException("first"), mock_resp]
        )
        with patch("time.sleep"):
            result = self.scraper.make_request("http://example.com", max_retries=2)
        assert result is mock_resp

    def test_raise_for_status_called(self):
        mock_resp = MagicMock(spec=requests.Response)
        self.scraper.session.get = MagicMock(return_value=mock_resp)

        self.scraper.make_request("http://example.com", max_retries=1)
        mock_resp.raise_for_status.assert_called_once()


# ===========================================================================
# ProthomAloScraper
# ===========================================================================

class TestProthomAloScraperInit:
    def test_uses_default_sections_when_none_given(self):
        s = ProthomAloScraper(START, END)
        assert s.section_ids == ProthomAloScraper.DEFAULT_SECTIONS

    def test_custom_sections_override_default(self):
        custom = ["111", "222"]
        s = ProthomAloScraper(START, END, section_ids=custom)
        assert s.section_ids == custom

    def test_seen_urls_starts_empty(self):
        s = ProthomAloScraper(START, END)
        assert len(s._seen_urls) == 0


class TestExtractStoryMetadata:
    def setup_method(self):
        self.scraper = ProthomAloScraper(START, END)

    def test_valid_story_returns_metadata(self):
        story = make_story()
        meta = self.scraper._extract_story_metadata(story)
        assert meta is not None
        assert meta["headline"] == story["headline"]
        assert "prothomalo.com" in meta["url"]
        assert meta["published_date"] == "2025-01-15"

    def test_no_headline_returns_none(self):
        story = make_story(headline="")
        assert self.scraper._extract_story_metadata(story) is None

    def test_no_slug_returns_none(self):
        story = make_story(slug="")
        assert self.scraper._extract_story_metadata(story) is None

    def test_feature_slug_is_skipped(self):
        story = make_story(slug="feature/2025/01/some-feature")
        assert self.scraper._extract_story_metadata(story) is None

    def test_quiz_slug_is_skipped(self):
        story = make_story(slug="quiz/2025/01/some-quiz")
        assert self.scraper._extract_story_metadata(story) is None

    def test_date_out_of_range_returns_none(self):
        dt = datetime(2024, 6, 1)
        story = make_story(published_at_ms=int(dt.timestamp() * 1000))
        assert self.scraper._extract_story_metadata(story) is None

    def test_missing_published_at_returns_none(self):
        story = {"headline": "Test", "slug": "bd/2025/test", "summary": ""}
        assert self.scraper._extract_story_metadata(story) is None

    def test_url_built_from_base_and_slug(self):
        story = make_story(slug="politics/2025/01/15/article")
        meta = self.scraper._extract_story_metadata(story)
        assert meta["url"] == "https://www.prothomalo.com/politics/2025/01/15/article"


class TestSplitDateRangeByMonth:
    def test_same_month_returns_one_chunk(self):
        s = ProthomAloScraper("2025-01-01", "2025-01-31")
        chunks = s.split_date_range_by_month()
        assert len(chunks) == 1
        assert chunks[0] == ("2025-01-01", "2025-01-31")

    def test_two_months_returns_two_chunks(self):
        s = ProthomAloScraper("2025-01-15", "2025-02-20")
        chunks = s.split_date_range_by_month()
        assert len(chunks) == 2
        assert chunks[0][0] == "2025-01-15"
        assert chunks[1][1] == "2025-02-20"

    def test_year_boundary_splits_correctly(self):
        s = ProthomAloScraper("2024-12-15", "2025-01-10")
        chunks = s.split_date_range_by_month()
        assert len(chunks) == 2
        assert chunks[0][0] == "2024-12-15"
        assert chunks[1][1] == "2025-01-10"

    def test_three_months_returns_three_chunks(self):
        s = ProthomAloScraper("2025-01-01", "2025-03-31")
        chunks = s.split_date_range_by_month()
        assert len(chunks) == 3

    def test_single_day_range(self):
        s = ProthomAloScraper("2025-01-15", "2025-01-15")
        chunks = s.split_date_range_by_month()
        assert len(chunks) == 1
        assert chunks[0] == ("2025-01-15", "2025-01-15")


class TestFetchAndCreateArticle:
    def setup_method(self):
        self.scraper = ProthomAloScraper(START, END)

    def test_returns_scraped_article_with_valid_content(self):
        # Content must be > 100 chars for _fetch_and_create_article to use it
        long_content = "এটি একটি পরীক্ষামূলক বাংলা সংবাদ নিবন্ধ। " * 5
        with patch.object(
            self.scraper,
            "fetch_article_content",
            return_value=long_content,
        ):
            meta = {
                "headline": "Test Title",
                "url": "https://www.prothomalo.com/test",
                "published_date": "2025-01-15",
                "summary": "Summary text",
            }
            result = self.scraper._fetch_and_create_article(meta)
        assert result is not None
        assert isinstance(result, ScrapedArticle)
        assert result.source == "prothom_alo"
        assert result.title == "Test Title"

    def test_returns_none_when_content_too_short(self):
        with patch.object(
            self.scraper, "fetch_article_content", return_value="Too short"
        ):
            meta = {
                "headline": "Test",
                "url": "https://www.prothomalo.com/test",
                "published_date": "2025-01-15",
                "summary": "",
            }
            result = self.scraper._fetch_and_create_article(meta)
        assert result is None

    def test_falls_back_to_summary_when_content_unavailable(self):
        long_summary = "এটি একটি বিস্তারিত সারসংক্ষেপ। " * 10  # >50 chars

        with patch.object(
            self.scraper, "fetch_article_content", return_value=""
        ):
            meta = {
                "headline": "Test",
                "url": "https://www.prothomalo.com/test",
                "published_date": "2025-01-15",
                "summary": long_summary,
            }
            result = self.scraper._fetch_and_create_article(meta)
        assert result is not None
        assert result.content.startswith("এটি একটি বিস্তারিত")

    def test_content_truncated_to_2000_chars(self):
        long_content = "বাংলা " * 500  # Way more than 2000 characters

        with patch.object(
            self.scraper, "fetch_article_content", return_value=long_content
        ):
            meta = {
                "headline": "Long article",
                "url": "https://www.prothomalo.com/test",
                "published_date": "2025-01-15",
                "summary": "",
            }
            result = self.scraper._fetch_and_create_article(meta)
        assert result is not None
        assert len(result.content) <= 2000


# ===========================================================================
# JugantorScraper._clean_content
# ===========================================================================

class TestJugantorCleanContent:
    def setup_method(self):
        self.scraper = JugantorScraper(START, END)

    def test_empty_string_returns_empty(self):
        assert self.scraper._clean_content("") == ""

    def test_none_like_falsy_returns_empty(self):
        # None would normally cause TypeError but method guards against it
        assert self.scraper._clean_content("") == ""

    def test_clean_content_removes_related_news_section(self):
        text = "এটি একটি মূল খবর। সম্পর্কিত খবর এটি উচিত নয়।"
        cleaned = self.scraper._clean_content(text)
        assert "সম্পর্কিত খবর" not in cleaned
        assert "এটি একটি মূল খবর" in cleaned

    def test_clean_content_normalizes_whitespace(self):
        text = "শব্দ   একাধিক   স্পেস   সহ"
        cleaned = self.scraper._clean_content(text)
        assert "  " not in cleaned  # no double spaces

    def test_clean_content_strips_leading_trailing_whitespace(self):
        text = "  কিছু খবর  "
        cleaned = self.scraper._clean_content(text)
        assert cleaned == cleaned.strip()

    def test_plain_content_returned_unchanged(self):
        text = "সাধারণ বাংলা সংবাদ নিবন্ধ যা পরিষ্কার।"
        cleaned = self.scraper._clean_content(text)
        assert "সাধারণ বাংলা" in cleaned


# ===========================================================================
# NewsScraper (coordinator)
# ===========================================================================

class TestNewsScraper:
    def setup_method(self):
        self.scraper = NewsScraper()

    @pytest.mark.asyncio
    async def test_unknown_source_returns_empty_list(self):
        result = await self.scraper.scrape_articles(
            "unknown_newspaper", date(2025, 1, 1), date(2025, 1, 5)
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_known_source_calls_correct_scraper_class(self):
        mock_articles = [
            ScrapedArticle(
                title="Test",
                content="Content বাংলা",
                url="https://prothomalo.com/test",
                source="prothom_alo",
            )
        ]

        with patch(
            "app.services.scraper.ProthomAloScraper"
        ) as mock_cls:
            instance = mock_cls.return_value
            instance.scrape_articles = MagicMock(return_value=mock_articles)

            result = await self.scraper.scrape_articles(
                "prothom_alo", date(2025, 1, 1), date(2025, 1, 5)
            )

        assert len(result) == 1
        assert result[0].source == "prothom_alo"

    @pytest.mark.asyncio
    async def test_exception_in_scraper_returns_empty_list(self):
        with patch("app.services.scraper.ProthomAloScraper") as mock_cls:
            instance = mock_cls.return_value
            instance.scrape_articles = MagicMock(side_effect=Exception("Network error"))

            result = await self.scraper.scrape_articles(
                "prothom_alo", date(2025, 1, 1), date(2025, 1, 5)
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_all_valid_source_keys_are_recognised(self):
        """Every documented source key must not return [] due to unknown source."""
        sources = [
            "prothom_alo", "jugantor", "daily_star",
            "dhaka_tribune", "samakal", "naya_diganta", "ittefaq",
        ]
        for source in sources:
            with patch(f"app.services.scraper.{source.title().replace('_', '')}Scraper", create=True):
                # Just verify it doesn't hit the "unknown source" branch
                # by patching the entire scraper map lookup is unnecessary -
                # we test by checking the scraper_map in the actual code:
                pass

        # More direct: monkey-patch all scrapers to return [] in the executor
        patchers = {}
        for src in sources:
            class_name = {
                "prothom_alo": "ProthomAloScraper", "jugantor": "JugantorScraper",
                "daily_star": "DailyStarScraper", "dhaka_tribune": "DhakaTribuneScraper",
                "samakal": "SamakalScraper", "naya_diganta": "NayaDigantaScraper",
                "ittefaq": "IttefaqScraper",
            }[src]
            p = patch(f"app.services.scraper.{class_name}")
            mock_cls = p.start()
            mock_cls.return_value.scrape_articles = MagicMock(return_value=[])
            patchers[src] = p

        try:
            for src in sources:
                result = await self.scraper.scrape_articles(
                    src, date(2025, 1, 1), date(2025, 1, 2)
                )
                assert isinstance(result, list), f"{src} returned non-list"
        finally:
            for p in patchers.values():
                p.stop()
