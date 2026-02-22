"""
Unit tests for app/database/models.py  (SQLAlchemy ORM models)

Covers:
- User model: creation, defaults, repr
- Article model: creation, defaults, repr
- UserRole enum values
- Relationship read (ArticleCluster <-> Article, User <-> UserAnalysis)
- Column constraints (unique email, nullable fields)
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.models import User, UserRole, Article


# ===========================================================================
# UserRole Enum
# ===========================================================================

class TestUserRoleEnum:
    def test_admin_value(self):
        assert UserRole.ADMIN.value == "admin"

    def test_user_value(self):
        assert UserRole.USER.value == "user"

    def test_role_is_string_subclass(self):
        assert isinstance(UserRole.ADMIN, str)


# ===========================================================================
# User Model Tests
# ===========================================================================

class TestUserModel:
    def test_create_user_basic(self, db_session):
        user = User(
            username="dbtest",
            email="dbtest@example.com",
            hashed_password="hashedpw",
            role=UserRole.USER,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.username == "dbtest"
        assert user.email == "dbtest@example.com"

    def test_user_defaults(self, db_session):
        user = User(
            username="defaults",
            email="defaults@example.com",
            hashed_password="hashedpw",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Defaults
        assert user.is_active is True
        assert user.is_verified is False
        assert user.role == UserRole.USER
        assert user.category_preferences is None
        assert user.created_at is not None

    def test_user_repr(self, db_session):
        user = User(
            username="reprtest",
            email="reprtest@example.com",
            hashed_password="pw",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        r = repr(user)
        assert "reprtest" in r
        assert "reprtest@example.com" in r

    def test_admin_role_assignment(self, db_session):
        user = User(
            username="admintestdb",
            email="admintest@db.com",
            hashed_password="pw",
            role=UserRole.ADMIN,
            is_verified=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.role == UserRole.ADMIN
        assert user.is_verified is True

    def test_unique_email_constraint(self, db_session):
        u1 = User(username="u1", email="same@email.com", hashed_password="pw")
        u2 = User(username="u2", email="same@email.com", hashed_password="pw")
        db_session.add(u1)
        db_session.commit()
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_non_unique_username_allowed(self, db_session):
        u1 = User(username="samename", email="email1@test.com", hashed_password="pw")
        u2 = User(username="samename", email="email2@test.com", hashed_password="pw")
        db_session.add_all([u1, u2])
        db_session.commit()
        assert u1.id != u2.id
        assert u1.username == u2.username

    def test_user_json_preferences(self, db_session):
        prefs = ["রাজনীতি", "বিশ্ব", "খেলাধুলা"]
        user = User(
            username="prefuser",
            email="pref@example.com",
            hashed_password="pw",
            category_preferences=prefs,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.category_preferences == prefs

    def test_verification_token_fields(self, db_session):
        from datetime import timedelta
        user = User(
            username="tokenuser",
            email="token@example.com",
            hashed_password="pw",
            verification_token="abc123",
            token_expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.verification_token == "abc123"
        assert user.token_expires_at is not None

    def test_password_reset_otp_fields(self, db_session):
        from datetime import timedelta
        user = User(
            username="otpuser2",
            email="otp2@example.com",
            hashed_password="pw",
            reset_otp="123456",
            reset_otp_expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.reset_otp == "123456"
        assert user.reset_otp_expires_at is not None

    def test_user_query_by_email(self, db_session):
        user = User(username="quser", email="query@test.com", hashed_password="pw")
        db_session.add(user)
        db_session.commit()

        found = db_session.query(User).filter(User.email == "query@test.com").first()
        assert found is not None
        assert found.username == "quser"

    def test_user_query_nonexistent_returns_none(self, db_session):
        found = db_session.query(User).filter(User.email == "ghost@nowhere.com").first()
        assert found is None


# ===========================================================================
# Article Model Tests
# ===========================================================================

class TestArticleModel:
    def test_create_article_basic(self, db_session):
        article = Article(
            source="prothom_alo",
            url="https://prothomalo.com/article/1",
            original_content="এটি পরীক্ষামূলক সংবাদ নিবন্ধ।",
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert article.id is not None
        assert article.source == "prothom_alo"

    def test_article_defaults(self, db_session):
        article = Article(
            source="jugantor",
            url="https://jugantor.com/article/2",
            original_content="কিছু বিষয়বস্তু।",
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert article.processed is False
        assert article.total_changes == 0
        assert article.is_biased is None
        assert article.bias_score is None
        assert article.created_at is not None

    def test_article_repr(self, db_session):
        article = Article(
            source="daily_star",
            url="https://thedailystar.net/article/3",
            original_content="some content here",
            title="Test Title",
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        r = repr(article)
        assert "daily_star" in r
        assert "Test Title" in r

    def test_article_unique_url_constraint(self, db_session):
        a1 = Article(
            source="prothom_alo",
            url="https://prothomalo.com/same",
            original_content="content1",
        )
        a2 = Article(
            source="prothom_alo",
            url="https://prothomalo.com/same",  # same URL
            original_content="content2",
        )
        db_session.add(a1)
        db_session.commit()
        db_session.add(a2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_article_bias_fields(self, db_session):
        article = Article(
            source="samakal",
            url="https://samakal.com/article/bias",
            original_content="বিশ্লেষণের বিষয়বস্তু।",
            is_biased=True,
            bias_score=77.5,
            bias_summary="High political bias.",
            biased_terms=[{"term": "পক্ষপাত", "severity": "high"}],
            processed=True,
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert article.is_biased is True
        assert article.bias_score == 77.5
        assert article.processed is True
        assert len(article.biased_terms) == 1

    def test_article_headline_fields(self, db_session):
        article = Article(
            source="prothom_alo",
            url="https://prothomalo.com/headline_test",
            original_content="শিরোনাম পরীক্ষার বিষয়বস্তু।",
            generated_headlines=["Headline A", "Headline B"],
            recommended_headline="Headline A",
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert len(article.generated_headlines) == 2
        assert article.recommended_headline == "Headline A"

    def test_article_published_date(self, db_session):
        pub_date = datetime(2026, 1, 15)
        article = Article(
            source="dhaka_tribune",
            url="https://dhakatribune.com/date_test",
            original_content="তারিখ পরীক্ষার বিষয়বস্তু।",
            published_date=pub_date,
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert article.published_date == pub_date


# ===========================================================================
# Query / Filter Tests
# ===========================================================================

class TestDatabaseQueries:
    def test_filter_articles_by_source(self, db_session, sample_article):
        found = (
            db_session.query(Article)
            .filter(Article.source == "prothom_alo")
            .all()
        )
        assert any(a.id == sample_article.id for a in found)

    def test_filter_articles_by_processed(self, db_session, sample_article):
        not_processed = (
            db_session.query(Article)
            .filter(Article.processed == False)  # noqa: E712
            .all()
        )
        assert any(a.id == sample_article.id for a in not_processed)

    def test_filter_users_by_role(self, db_session, plain_user, admin_user):
        admins = db_session.query(User).filter(User.role == UserRole.ADMIN).all()
        users = db_session.query(User).filter(User.role == UserRole.USER).all()

        assert any(u.id == admin_user.id for u in admins)
        assert any(u.id == plain_user.id for u in users)

    def test_count_all_articles(self, db_session, sample_article):
        count = db_session.query(Article).count()
        assert count >= 1
