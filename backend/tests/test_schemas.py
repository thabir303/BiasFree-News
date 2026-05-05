"""
Unit tests for app/models/schemas.py  (Pydantic models)

Covers:
- UserSignup validation (username length, email format, password length)
- UserSignin validation
- ArticleInput validation (min_length, max_length)
- ScrapeRequest validation (source enum, date range)
- BiasedTerm / ContentChange / BiasAnalysisResponse construction
- HeadlineResponse / DebiasResponse / FullProcessResponse construction
- ForgotPasswordRequest / VerifyOtpRequest / ResetPasswordRequest validation
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from datetime import date
from pydantic import ValidationError

from app.models.schemas import (
    UserSignup,
    UserSignin,
    ArticleInput,
    ScrapeRequest,
    BiasedTerm,
    BiasAnalysisResponse,
    ContentChange,
    DebiasResponse,
    HeadlineResponse,
    FullProcessResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    UpdateUsernameRequest,
    CategoryPreferencesRequest,
)


# ===========================================================================
# UserSignup
# ===========================================================================

class TestUserSignup:
    def test_valid_signup(self):
        u = UserSignup(username="validuser", email="a@b.com", password="pass12")
        assert u.username == "validuser"
        assert u.email == "a@b.com"

    def test_username_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserSignup(username="ab", email="a@b.com", password="pass12")

    def test_username_too_long_raises(self):
        with pytest.raises(ValidationError):
            UserSignup(username="a" * 51, email="a@b.com", password="pass12")

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserSignup(username="validuser", email="not-an-email", password="pass12")

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserSignup(username="validuser", email="a@b.com", password="abc")

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            UserSignup(username="valid")


# ===========================================================================
# UserSignin
# ===========================================================================

class TestUserSignin:
    def test_valid_signin(self):
        s = UserSignin(email="a@b.com", password="mypassword")
        assert s.email == "a@b.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserSignin(email="badformat", password="pass")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            UserSignin(email="a@b.com")


# ===========================================================================
# ArticleInput
# ===========================================================================

class TestArticleInput:
    VALID_CONTENT = "এটি একটি বৈধ বাংলা নিবন্ধের বিষয়বস্তু যা ৫০ অক্ষরের বেশি।" * 2

    def test_valid_article_input(self):
        a = ArticleInput(content=self.VALID_CONTENT)
        assert len(a.content) >= 50

    def test_content_too_short_raises(self):
        with pytest.raises(ValidationError):
            ArticleInput(content="short")

    def test_content_stripped_whitespace(self):
        a = ArticleInput(content="  " + self.VALID_CONTENT + "  ")
        assert not a.content.startswith(" ")

    def test_optional_title_accepted(self):
        a = ArticleInput(content=self.VALID_CONTENT, title="My Title")
        assert a.title == "My Title"

    def test_content_exceeds_max_length_raises(self):
        with pytest.raises(ValidationError):
            ArticleInput(content="ক" * 10000)


# ===========================================================================
# ScrapeRequest
# ===========================================================================

class TestScrapeRequest:
    def test_valid_scrape_request(self):
        req = ScrapeRequest(
            source="prothom_alo",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )
        assert req.source == "prothom_alo"

    def test_source_normalised_to_lowercase(self):
        req = ScrapeRequest(
            source="Prothom_Alo",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )
        assert req.source == "prothom_alo"

    def test_invalid_source_raises(self):
        with pytest.raises(ValidationError):
            ScrapeRequest(
                source="unknown_paper",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 5),
            )

    def test_end_before_start_raises(self):
        with pytest.raises(ValidationError):
            ScrapeRequest(
                source="prothom_alo",
                start_date=date(2026, 1, 10),
                end_date=date(2026, 1, 1),
            )

    def test_all_valid_sources_accepted(self):
        for src in ["prothom_alo", "jugantor", "daily_star", "dhaka_tribune", "samakal"]:
            req = ScrapeRequest(
                source=src,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 5),
            )
            assert req.source == src


# ===========================================================================
# BiasedTerm
# ===========================================================================

class TestBiasedTerm:
    def test_valid_biased_term(self):
        t = BiasedTerm(
            term="পক্ষপাত",
            reason="Loaded language",
            neutral_alternative="মতভেদ",
            severity="medium",
        )
        assert t.term == "পক্ষপাত"
        assert t.severity == "medium"

    def test_optional_position_defaults_none(self):
        t = BiasedTerm(
            term="x", reason="r", neutral_alternative="y", severity="low"
        )
        assert t.position is None

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            BiasedTerm(term="x", reason="r")  # missing neutral_alternative & severity


# ===========================================================================
# BiasAnalysisResponse
# ===========================================================================

class TestBiasAnalysisResponse:
    def test_valid_response(self):
        r = BiasAnalysisResponse(
            is_biased=True,
            bias_score=72.0,
            biased_terms=[],
            summary="Some bias detected",
            confidence=0.9,
        )
        assert r.bias_score == 72.0
        assert r.confidence == 0.9

    def test_bias_score_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            BiasAnalysisResponse(
                is_biased=False,
                bias_score=110.0,  # > 100
                biased_terms=[],
                summary="s",
                confidence=0.5,
            )

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            BiasAnalysisResponse(
                is_biased=False,
                bias_score=50.0,
                biased_terms=[],
                summary="s",
                confidence=1.5,  # > 1.0
            )


# ===========================================================================
# ContentChange / DebiasResponse
# ===========================================================================

class TestDebiasResponse:
    def test_valid_debias_response(self):
        r = DebiasResponse(
            original_content="orig",
            debiased_content="debiased",
            changes=[ContentChange(original="o", debiased="d", reason="r")],
            total_changes=1,
        )
        assert r.total_changes == 1
        assert len(r.changes) == 1

    def test_empty_changes_allowed(self):
        r = DebiasResponse(
            original_content="orig",
            debiased_content="orig",
            changes=[],
            total_changes=0,
        )
        assert r.total_changes == 0


# ===========================================================================
# HeadlineResponse
# ===========================================================================

class TestHeadlineResponse:
    def test_valid_headline_response(self):
        r = HeadlineResponse(
            original_title="Old",
            generated_headlines=["New 1", "New 2"],
            recommended_headline="New 1",
            reasoning="Most neutral",
        )
        assert r.recommended_headline == "New 1"
        assert len(r.generated_headlines) == 2

    def test_no_original_title_allowed(self):
        r = HeadlineResponse(
            generated_headlines=["New 1"],
            recommended_headline="New 1",
            reasoning="reason",
        )
        assert r.original_title is None


# ===========================================================================
# Password Reset Schemas
# ===========================================================================

class TestPasswordResetSchemas:
    def test_forgot_password_valid(self):
        r = ForgotPasswordRequest(email="a@b.com")
        assert r.email == "a@b.com"

    def test_forgot_password_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="bad")

    def test_verify_otp_valid(self):
        r = VerifyOtpRequest(email="a@b.com", otp="123456")
        assert r.otp == "123456"

    def test_verify_otp_short_otp_raises(self):
        with pytest.raises(ValidationError):
            VerifyOtpRequest(email="a@b.com", otp="123")

    def test_verify_otp_long_otp_raises(self):
        with pytest.raises(ValidationError):
            VerifyOtpRequest(email="a@b.com", otp="1234567")

    def test_reset_password_valid(self):
        r = ResetPasswordRequest(email="a@b.com", otp="123456", new_password="newpass1")
        assert r.new_password == "newpass1"

    def test_reset_password_short_password_raises(self):
        with pytest.raises(ValidationError):
            ResetPasswordRequest(email="a@b.com", otp="123456", new_password="abc")


# ===========================================================================
# UpdateUsernameRequest
# ===========================================================================

class TestUpdateUsernameRequest:
    def test_valid_request(self):
        r = UpdateUsernameRequest(new_username="newname")
        assert r.new_username == "newname"

    def test_short_username_raises(self):
        with pytest.raises(ValidationError):
            UpdateUsernameRequest(new_username="ab")

    def test_long_username_raises(self):
        with pytest.raises(ValidationError):
            UpdateUsernameRequest(new_username="a" * 51)


# ===========================================================================
# CategoryPreferencesRequest
# ===========================================================================

class TestCategoryPreferences:
    def test_valid_preferences(self):
        r = CategoryPreferencesRequest(categories=["রাজনীতি", "বিশ্ব"])
        assert len(r.categories) == 2

    def test_empty_categories_raises(self):
        with pytest.raises(ValidationError):
            CategoryPreferencesRequest(categories=[])


# ===========================================================================
# Enhanced schemas validators (app/models/enhanced_schemas.py)
# ===========================================================================

class TestEnhancedArticleInput:
    """Tests that exercise the validator in enhanced_schemas.ArticleInput."""

    def test_content_exceeding_max_length_raises(self):
        from app.models.enhanced_schemas import ArticleInput as EnhancedArticleInput
        with pytest.raises(ValidationError):
            EnhancedArticleInput(content="ক" * 10000)

    def test_valid_content_is_accepted(self):
        from app.models.enhanced_schemas import ArticleInput as EnhancedArticleInput
        article = EnhancedArticleInput(content="এটি একটি বৈধ বাংলা নিবন্ধ। " * 5)
        assert len(article.content) > 0

    def test_content_is_stripped(self):
        from app.models.enhanced_schemas import ArticleInput as EnhancedArticleInput
        padded = "  " + "বাংলা সংবাদ নিবন্ধ। " * 5 + "  "
        article = EnhancedArticleInput(content=padded)
        assert not article.content.startswith(" ")


class TestBatchArticleInput:
    """Tests for the batch validator in enhanced_schemas.BatchArticleInput."""

    def test_too_many_articles_raises(self):
        from app.models.enhanced_schemas import ArticleInput as EnhancedArticleInput
        from app.models.enhanced_schemas import BatchArticleInput
        valid_article = EnhancedArticleInput(content="বাংলা সংবাদ নিবন্ধ। " * 5)
        with pytest.raises(ValidationError):
            BatchArticleInput(articles=[valid_article] * 21)

    def test_valid_batch_accepted(self):
        from app.models.enhanced_schemas import ArticleInput as EnhancedArticleInput
        from app.models.enhanced_schemas import BatchArticleInput
        valid_article = EnhancedArticleInput(content="বাংলা সংবাদ নিবন্ধ। " * 5)
        batch = BatchArticleInput(articles=[valid_article])
        assert len(batch.articles) == 1
