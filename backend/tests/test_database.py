"""
Unit tests for app/database/database.py

Covers:
- init_db() creates all tables
- _run_migrations() adds missing columns gracefully
- get_db() yields a valid session and closes it
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
import sqlite3
import tempfile
import os as _os
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


class TestGetDb:
    def test_get_db_yields_session(self):
        from app.database.database import get_db
        gen = get_db()
        db = next(gen)
        assert db is not None
        assert isinstance(db, Session)
        # Close the generator cleanly
        try:
            next(gen)
        except StopIteration:
            pass
        finally:
            db.close()

    def test_get_db_session_closed_after_use(self):
        """Session must not raise on close."""
        from app.database.database import get_db
        gen = get_db()
        db = next(gen)
        db.close()
        # Exhaust the generator
        try:
            next(gen)
        except StopIteration:
            pass


class TestInitDb:
    def test_init_db_creates_tables(self):
        """init_db() should create the users and articles tables."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name

        try:
            import app.database.database as db_module
            original_path = db_module.DATABASE_PATH
            original_url = db_module.DATABASE_URL

            # Point the module at a temp DB
            db_module.DATABASE_PATH = tmp_path
            db_module.DATABASE_URL = f"sqlite:///{tmp_path}"

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import StaticPool
            tmp_engine = create_engine(
                f"sqlite:///{tmp_path}",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            db_module.engine = tmp_engine
            db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)

            db_module.init_db()

            # Verify tables exist
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            assert "users" in tables
            assert "articles" in tables
        finally:
            db_module.DATABASE_PATH = original_path
            db_module.DATABASE_URL = original_url
            _os.unlink(tmp_path)

    def test_init_db_is_idempotent(self):
        """Calling init_db() twice should not raise."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            import app.database.database as db_module

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import StaticPool
            tmp_engine = create_engine(
                f"sqlite:///{tmp_path}",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            db_module.engine = tmp_engine
            db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)
            db_module.DATABASE_PATH = tmp_path

            db_module.init_db()
            db_module.init_db()  # Second call must not raise
        finally:
            _os.unlink(tmp_path)


class TestRunMigrations:
    def test_migrations_add_reset_otp_columns(self):
        """_run_migrations should add reset_otp and reset_otp_expires_at columns."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            # Create a minimal users table WITHOUT the OTP columns
            conn = sqlite3.connect(tmp_path)
            conn.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)"
            )
            conn.commit()
            conn.close()

            import app.database.database as db_module
            original = db_module.DATABASE_PATH
            db_module.DATABASE_PATH = tmp_path
            try:
                db_module._run_migrations()
            finally:
                db_module.DATABASE_PATH = original

            # Verify columns were added
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            cols = {row[1] for row in cursor.fetchall()}
            conn.close()
            assert "reset_otp" in cols
            assert "reset_otp_expires_at" in cols
        finally:
            _os.unlink(tmp_path)

    def test_migrations_skip_existing_columns(self):
        """_run_migrations must not fail when OTP columns already exist."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, reset_otp TEXT, reset_otp_expires_at DATETIME)"
            )
            conn.commit()
            conn.close()

            import app.database.database as db_module
            original = db_module.DATABASE_PATH
            db_module.DATABASE_PATH = tmp_path
            try:
                db_module._run_migrations()  # should not raise
            finally:
                db_module.DATABASE_PATH = original
        finally:
            _os.unlink(tmp_path)

    def test_migrations_graceful_when_no_table(self):
        """_run_migrations must not crash on empty database (no users table yet)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            import app.database.database as db_module
            original = db_module.DATABASE_PATH
            db_module.DATABASE_PATH = tmp_path
            try:
                db_module._run_migrations()  # should silently pass
            finally:
                db_module.DATABASE_PATH = original
        finally:
            _os.unlink(tmp_path)
