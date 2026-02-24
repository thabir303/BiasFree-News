"""Database connection and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.database.models import Base
from app.config import settings
import os

# ── Database URL ────────────────────────────────────────────────────
# Production: Use DATABASE_URL env var (PostgreSQL on Render)
# Development: Fall back to local SQLite file
_EXTERNAL_DB_URL = os.environ.get("DATABASE_URL", "")

if _EXTERNAL_DB_URL:
    # Render provides postgres:// but SQLAlchemy 2.x requires postgresql://
    if _EXTERNAL_DB_URL.startswith("postgres://"):
        _EXTERNAL_DB_URL = _EXTERNAL_DB_URL.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = _EXTERNAL_DB_URL
    IS_SQLITE = False
else:
    DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "biasfree.db"
    )
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    IS_SQLITE = True

# ── Engine creation ─────────────────────────────────────────────────
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_timeout=60,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
else:
    # PostgreSQL engine for production
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_timeout=60,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables and run migrations."""
    Base.metadata.create_all(bind=engine)
    
    # Run lightweight migrations for new columns on existing tables
    _run_migrations()


def _run_migrations():
    """Add new columns to existing tables.
    For SQLite: uses direct sqlite3 ALTER TABLE.
    For PostgreSQL: uses SQLAlchemy inspect to check & add columns.
    """
    if IS_SQLITE:
        _run_sqlite_migrations()
    else:
        _run_pg_migrations()


def _run_sqlite_migrations():
    """SQLite-specific lightweight migrations."""
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "reset_otp" not in existing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp VARCHAR(6)")
        if "reset_otp_expires_at" not in existing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expires_at DATETIME")
        conn.commit()
    except Exception:
        pass

    try:
        cursor.execute("PRAGMA table_info(article_clusters)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "pairwise_similarities" not in existing_columns:
            cursor.execute("ALTER TABLE article_clusters ADD COLUMN pairwise_similarities TEXT")
        conn.commit()
    except Exception:
        pass

    conn.close()


def _run_pg_migrations():
    """PostgreSQL lightweight migrations — add missing columns."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    def _has_column(table: str, column: str) -> bool:
        cols = {c["name"] for c in inspector.get_columns(table)}
        return column in cols

    with engine.begin() as conn:
        try:
            if not _has_column("users", "reset_otp"):
                conn.execute(text("ALTER TABLE users ADD COLUMN reset_otp VARCHAR(6)"))
            if not _has_column("users", "reset_otp_expires_at"):
                conn.execute(text("ALTER TABLE users ADD COLUMN reset_otp_expires_at TIMESTAMP"))
        except Exception:
            pass

        try:
            if not _has_column("article_clusters", "pairwise_similarities"):
                conn.execute(text("ALTER TABLE article_clusters ADD COLUMN pairwise_similarities TEXT"))
        except Exception:
            pass


def get_db() -> Session:
    """
    Dependency for getting database session.
    Use with FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
