"""
Database connection and session management.
"""
from collections.abc import Generator
from typing import Annotated

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
from app.database.models import Base
from app.config import settings
import os

# SQLite database file path
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "biasfree.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Disable SQL logging
)

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
    finally:
        conn.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    Use with FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for dependency injection (Annotated pattern)
DB = Annotated[Session, Depends(get_db)]
