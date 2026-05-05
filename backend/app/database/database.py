"""
Database connection and session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.database.models import Base
from app.config import settings
import os

# SQLite database file path
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "biasfree.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with tuned pool settings to avoid QueuePool exhaustion
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,  # Disable SQL logging
    poolclass=QueuePool,
    pool_size=20,       # Increase from default 5
    max_overflow=30,    # Increase from default 10
    pool_timeout=60,    # Increase from default 30s
    pool_pre_ping=True, # Verify connections before use
    pool_recycle=1800,  # Recycle connections every 30 min
)

# Enable WAL mode for better SQLite concurrency
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables and run migrations."""
    Base.metadata.create_all(bind=engine)
    
    # Run lightweight migrations for new columns on existing tables
    _run_migrations()


def _run_migrations():
    """Add new columns to existing tables (SQLite doesn't auto-add via create_all)."""
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check and add reset_otp columns to users table
    try:
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        if "reset_otp" not in existing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp VARCHAR(6)")
        if "reset_otp_expires_at" not in existing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expires_at DATETIME")
        
        conn.commit()
    except Exception:
        pass  # Table may not exist yet — create_all will handle it

    # Add pairwise_similarities column to article_clusters
    try:
        cursor.execute("PRAGMA table_info(article_clusters)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        if "pairwise_similarities" not in existing_columns:
            cursor.execute("ALTER TABLE article_clusters ADD COLUMN pairwise_similarities TEXT")
        
        conn.commit()
    except Exception:
        pass

    conn.close()


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
