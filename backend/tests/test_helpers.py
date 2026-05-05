"""
Unit tests for app/utils/helpers.py

Full coverage of every exported utility function:
- format_date
- truncate_text
- calculate_word_count
- clean_html_text
- extract_domain
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from datetime import datetime

from app.utils.helpers import (
    format_date,
    truncate_text,
    calculate_word_count,
    clean_html_text,
    extract_domain,
)


# ===========================================================================
# format_date
# ===========================================================================

class TestFormatDate:
    def test_default_format_is_iso_date(self):
        dt = datetime(2025, 3, 15, 10, 30)
        assert format_date(dt) == "2025-03-15"

    def test_custom_format(self):
        dt = datetime(2025, 3, 15)
        assert format_date(dt, "%d/%m/%Y") == "15/03/2025"

    def test_year_only_format(self):
        dt = datetime(2025, 6, 1)
        assert format_date(dt, "%Y") == "2025"

    def test_full_datetime_format(self):
        dt = datetime(2025, 1, 1, 12, 0, 0)
        assert format_date(dt, "%Y-%m-%d %H:%M:%S") == "2025-01-01 12:00:00"


# ===========================================================================
# truncate_text
# ===========================================================================

class TestTruncateText:
    def test_short_text_is_returned_unchanged(self):
        assert truncate_text("hello", 100) == "hello"

    def test_text_exactly_at_limit_is_unchanged(self):
        text = "a" * 1500
        assert truncate_text(text, 1500) == text

    def test_long_text_is_truncated(self):
        text = " ".join(["word"] * 1000)  # well over 1500 default
        result = truncate_text(text)
        assert len(result) <= 1500 + len("...")

    def test_truncated_text_ends_with_suffix(self):
        text = " ".join(["word"] * 1000)
        result = truncate_text(text)
        assert result.endswith("...")

    def test_custom_max_length(self):
        text = "একটি দুটি তিনটি চারটি পাঁচটি"
        result = truncate_text(text, max_length=10)
        assert len(result) <= 10 + len("...")

    def test_custom_suffix(self):
        text = "word " * 500
        result = truncate_text(text, max_length=50, suffix="—")
        assert result.endswith("—")

    def test_empty_string(self):
        assert truncate_text("", 100) == ""


# ===========================================================================
# calculate_word_count
# ===========================================================================

class TestCalculateWordCount:
    def test_simple_sentence(self):
        assert calculate_word_count("hello world") == 2

    def test_empty_string_returns_zero(self):
        # str.split() on "" gives [], so count is 0
        result = calculate_word_count("")
        assert result == 0

    def test_single_word(self):
        assert calculate_word_count("word") == 1

    def test_multiple_spaces_counted_once(self):
        # "a  b" → split() → ['a', 'b']
        assert calculate_word_count("a  b") == 2

    def test_bengali_text(self):
        text = "এটি একটি পরীক্ষামূলক বাক্য"
        assert calculate_word_count(text) == 4

    def test_ten_words(self):
        text = " ".join(["word"] * 10)
        assert calculate_word_count(text) == 10


# ===========================================================================
# clean_html_text
# ===========================================================================

class TestCleanHtmlText:
    def test_removes_simple_tags(self):
        result = clean_html_text("<p>Hello</p>")
        assert result == "Hello"

    def test_removes_nested_tags(self):
        result = clean_html_text("<div><span>Hello</span> World</div>")
        assert result == "Hello World"

    def test_plain_text_unchanged(self):
        assert clean_html_text("plain text") == "plain text"

    def test_collapses_extra_whitespace(self):
        result = clean_html_text("word1   word2")
        assert result == "word1 word2"

    def test_strips_leading_trailing_whitespace(self):
        result = clean_html_text("  text  ")
        assert result == "text"

    def test_self_closing_tags_removed(self):
        result = clean_html_text("line1<br/>line2")
        assert "<" not in result

    def test_empty_string(self):
        assert clean_html_text("") == ""

    def test_mixed_html_and_text(self):
        result = clean_html_text("<h1>Title</h1><p>Body text here.</p>")
        assert "Title" in result
        assert "Body text here." in result
        assert "<" not in result


# ===========================================================================
# extract_domain
# ===========================================================================

class TestExtractDomain:
    def test_extracts_domain_from_http_url(self):
        assert extract_domain("http://example.com/page") == "example.com"

    def test_extracts_domain_from_https_url(self):
        assert extract_domain("https://www.prothomalo.com/article") == "www.prothomalo.com"

    def test_url_with_path_and_query(self):
        result = extract_domain("https://daily-star.com/news?id=123")
        assert result == "daily-star.com"

    def test_url_with_port(self):
        result = extract_domain("http://localhost:8000/api")
        assert result == "localhost:8000"

    def test_empty_string_returns_empty_domain(self):
        result = extract_domain("")
        # urlparse("").netloc == ""
        assert result == ""

    def test_invalid_url_returns_empty_or_none(self):
        result = extract_domain("not-a-url")
        # urlparse gives netloc="" for relative paths
        assert result in ("", None)

    def test_exception_in_urlparse_returns_none(self):
        """Covers the except Exception: return None branch (lines 86-87)."""
        from unittest.mock import patch
        with patch("urllib.parse.urlparse", side_effect=Exception("parse error")):
            result = extract_domain("http://example.com")
        assert result is None
