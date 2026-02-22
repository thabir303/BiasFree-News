"""
Shared pytest fixtures for all backend unit tests.
Uses an in-memory SQLite database so tests are isolated and fast.

Key design decisions:
- `test_client` is module-scoped to avoid event-loop conflicts from the FastAPI
  lifespan (which starts a scheduler).  The lifespan is patched out in tests so
  the scheduler / Redis init never runs.
- `db_session` is function-scoped: each test gets its own transactional session
  that is rolled back after the test (full isolation without touching the schema).
"""
import os
# Force test environment variables BEFORE any app import touches settings
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "test-password")
os.environ.setdefault("MAIL_FROM", "test@example.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")
os.environ.setdefault("ENVIRONMENT", "test")

from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.models import Base, User, UserRole, Article
from app.database.database import get_db
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared per test session)
# StaticPool ensures ALL engine.connect() calls use the same single connection
# so transaction rollbacks in db_session truly isolate each test.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once at the start of the session."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    """
    Provide a fully isolated db session per test.

    Drops and recreates all tables before each test so there is no data
    leakage between tests.  The in-memory SQLite engine is fast enough to
    make this practical.
    """
    # Clean slate for every test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Null lifespan – replaces the real one that starts the APScheduler & Redis
# ---------------------------------------------------------------------------
@asynccontextmanager
async def _null_lifespan(app):
    """No-op lifespan: tables are already created by create_tables fixture."""
    yield


@pytest.fixture()
def test_client(db_session):
    """
    FastAPI TestClient (function-scoped) with:
    - The real lifespan replaced by a null context so no scheduler/Redis starts
    - The DB dependency overridden to use the test's transactional db_session
    - app.database.database.get_db also patched at module level so that
      get_current_user's manual call to next(get_db()) also hits the test DB
    - Email sending stubbed out
    """
    from app.main import app
    import app.database.database as db_module

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _null_lifespan

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Patch the module-level get_db so manual next(get_db()) calls also use test DB
    original_get_db = db_module.get_db

    def patched_get_db():
        yield db_session

    db_module.get_db = patched_get_db
    app.dependency_overrides[get_db] = override_get_db

    with patch("app.services.email_service.email_service.send_verification_email", return_value=True), \
         patch("app.services.email_service.email_service.send_password_reset_otp", return_value=True), \
         patch("app.services.email_service.email_service.send_password_reset_email", return_value=True):
        client = TestClient(app, raise_server_exceptions=True)
        yield client

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan
    db_module.get_db = original_get_db


@pytest.fixture()
def api_db_session(test_client):
    """
    Expose the module-level DB session used by test_client.
    Use this in integration tests that need to pre-populate or read data
    from the same DB the running API sees.
    """
    # Access the module_session from the app's dependency override
    from app.main import app
    db_gen = app.dependency_overrides[get_db]()
    session = next(db_gen)
    yield session


# ---------------------------------------------------------------------------
# Helper: pre-built users  (function-scoped for isolation)
# ---------------------------------------------------------------------------

@pytest.fixture()
def plain_user(db_session):
    """A regular, fully verified user in the test DB."""
    hashed_pw = AuthService.hash_password("testpassword123")
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hashed_pw,
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session):
    """An admin user in the test DB."""
    hashed_pw = AuthService.hash_password("adminpassword123")
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hashed_pw,
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def unverified_user(db_session):
    """A user whose email is NOT yet verified."""
    from datetime import datetime, timedelta
    hashed_pw = AuthService.hash_password("password123")
    user = User(
        username="unverifieduser",
        email="unverified@example.com",
        hashed_password=hashed_pw,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
        verification_token="valid-test-token",
        token_expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def inactive_user(db_session):
    """A deactivated user."""
    hashed_pw = AuthService.hash_password("password123")
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password=hashed_pw,
        role=UserRole.USER,
        is_active=False,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def sample_article(db_session):
    """A minimal article record."""
    from datetime import datetime
    article = Article(
        source="prothom_alo",
        category="রাজনীতি",
        url="https://www.prothomalo.com/test/article/123",
        title="Test Article Title",
        original_content="এটি একটি পরীক্ষামূলক সংবাদ নিবন্ধ। এতে রাজনৈতিক পক্ষপাত থাকতে পারে।",
        published_date=datetime.utcnow(),
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


@pytest.fixture()
def auth_headers(plain_user):
    """Bearer auth headers for the plain_user fixture."""
    token = AuthService.create_access_token(
        data={
            "sub": str(plain_user.id),
            "email": plain_user.email,
            "role": plain_user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_auth_headers(admin_user):
    """Bearer auth headers for the admin_user fixture."""
    token = AuthService.create_access_token(
        data={
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "role": admin_user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}

