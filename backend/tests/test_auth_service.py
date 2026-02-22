"""
Unit tests for app/services/auth_service.py

Tests cover:
- Password hashing & verification
- JWT token creation & decoding
- User creation (happy path + duplicate email)
- User authentication (correct, wrong password, inactive, unverified)
- Email verification (valid token, expired token, invalid token)
- Admin user creation
- Helper lookups (get_user_by_id, get_user_by_email)
- generate_verification_token randomness
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.database.models import User, UserRole
from app.models.schemas import UserSignup


# ===========================================================================
# Password Hashing Tests
# ===========================================================================

class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        hashed = AuthService.hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = AuthService.hash_password("mysecret")
        assert AuthService.verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = AuthService.hash_password("mysecret")
        assert AuthService.verify_password("wrongpass", hashed) is False

    def test_same_password_different_hashes(self):
        h1 = AuthService.hash_password("samepass")
        h2 = AuthService.hash_password("samepass")
        # bcrypt salts mean the same password yields different hashes
        assert h1 != h2

    def test_empty_password_hashes(self):
        hashed = AuthService.hash_password("")
        assert AuthService.verify_password("", hashed) is True


# ===========================================================================
# JWT Token Tests
# ===========================================================================

class TestJWTTokens:
    def test_create_and_decode_token(self):
        payload = {"sub": "42", "email": "a@b.com", "role": "user"}
        token = AuthService.create_access_token(data=payload)
        decoded = AuthService.decode_token(token)
        assert decoded["sub"] == "42"
        assert decoded["email"] == "a@b.com"
        assert decoded["role"] == "user"

    def test_token_contains_exp_and_iat(self):
        token = AuthService.create_access_token(data={"sub": "1"})
        decoded = AuthService.decode_token(token)
        assert "exp" in decoded
        assert "iat" in decoded

    def test_custom_expiry_respected(self):
        import time as _time
        delta = timedelta(minutes=5)
        before_secs = int(_time.time())
        token = AuthService.create_access_token(data={"sub": "1"}, expires_delta=delta)
        after_secs = int(_time.time())
        decoded = AuthService.decode_token(token)
        # JWT exp is an integer UTC timestamp; allow ±5 s tolerance
        exp_secs = decoded["exp"]
        expected_low = before_secs + int(delta.total_seconds())
        expected_high = after_secs + int(delta.total_seconds()) + 5
        assert expected_low <= exp_secs <= expected_high, (
            f"exp {exp_secs} not in [{expected_low}, {expected_high}]"
        )

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            AuthService.decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = AuthService.create_access_token(data={"sub": "99"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            AuthService.decode_token(tampered)
        assert exc_info.value.status_code == 401


# ===========================================================================
# Verification Token Tests
# ===========================================================================

class TestVerificationToken:
    def test_token_is_string(self):
        token = AuthService.generate_verification_token()
        assert isinstance(token, str)

    def test_token_minimum_length(self):
        token = AuthService.generate_verification_token()
        assert len(token) >= 20

    def test_tokens_are_unique(self):
        tokens = {AuthService.generate_verification_token() for _ in range(20)}
        assert len(tokens) == 20


# ===========================================================================
# User Creation Tests
# ===========================================================================

class TestCreateUser:
    def test_create_user_success(self, db_session):
        user_data = UserSignup(
            username="newuser",
            email="newuser@example.com",
            password="password123",
        )
        user = AuthService.create_user(db_session, user_data)
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_verified is False
        assert user.role == UserRole.USER
        assert user.hashed_password != "password123"

    def test_create_user_password_is_hashed(self, db_session):
        user_data = UserSignup(
            username="hashtest",
            email="hashtest@example.com",
            password="plain123",
        )
        user = AuthService.create_user(db_session, user_data)
        assert AuthService.verify_password("plain123", user.hashed_password)

    def test_create_user_has_verification_token(self, db_session):
        user_data = UserSignup(
            username="tokentest",
            email="tokentest@example.com",
            password="password123",
        )
        user = AuthService.create_user(db_session, user_data)
        assert user.verification_token is not None
        assert user.token_expires_at is not None

    def test_duplicate_email_raises_400(self, db_session):
        user_data = UserSignup(
            username="duptest",
            email="dup@example.com",
            password="password123",
        )
        AuthService.create_user(db_session, user_data)
        with pytest.raises(HTTPException) as exc_info:
            AuthService.create_user(db_session, user_data)
        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()

    def test_duplicate_username_allowed_with_different_email(self, db_session):
        """Username is NOT unique; only email must be unique."""
        user1_data = UserSignup(
            username="sameusername",
            email="user1@example.com",
            password="password123",
        )
        user2_data = UserSignup(
            username="sameusername",
            email="user2@example.com",
            password="password456",
        )
        u1 = AuthService.create_user(db_session, user1_data)
        u2 = AuthService.create_user(db_session, user2_data)
        assert u1.id != u2.id
        assert u1.username == u2.username

    def test_create_admin_role_user(self, db_session):
        user_data = UserSignup(
            username="adminrole",
            email="adminrole@example.com",
            password="password123",
        )
        user = AuthService.create_user(db_session, user_data, role=UserRole.ADMIN)
        assert user.role == UserRole.ADMIN


# ===========================================================================
# User Authentication Tests
# ===========================================================================

class TestAuthenticateUser:
    def test_authenticate_valid_user(self, db_session, plain_user):
        result = AuthService.authenticate_user(
            db_session, plain_user.email, "testpassword123"
        )
        assert result is not None
        assert result != "not_verified"
        assert result.id == plain_user.id

    def test_authenticate_wrong_password_returns_none(self, db_session, plain_user):
        result = AuthService.authenticate_user(
            db_session, plain_user.email, "wrongpassword"
        )
        assert result is None

    def test_authenticate_nonexistent_email_returns_none(self, db_session):
        result = AuthService.authenticate_user(
            db_session, "nobody@nowhere.com", "password"
        )
        assert result is None

    def test_authenticate_unverified_returns_marker(self, db_session, unverified_user):
        result = AuthService.authenticate_user(
            db_session, unverified_user.email, "password123"
        )
        assert result == "not_verified"

    def test_authenticate_inactive_user_returns_none(self, db_session, inactive_user):
        result = AuthService.authenticate_user(
            db_session, inactive_user.email, "password123"
        )
        assert result is None


# ===========================================================================
# Email Verification Tests
# ===========================================================================

class TestVerifyEmail:
    def test_verify_with_valid_token(self, db_session, unverified_user):
        success = AuthService.verify_email(db_session, "valid-test-token")
        assert success is True
        db_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        assert unverified_user.verification_token is None

    def test_verify_with_invalid_token(self, db_session):
        success = AuthService.verify_email(db_session, "completely-wrong-token")
        assert success is False

    def test_verify_with_expired_token(self, db_session):
        from app.database.models import User, UserRole
        expired_user = User(
            username="expiredtoken",
            email="expiredtoken@example.com",
            hashed_password=AuthService.hash_password("password"),
            role=UserRole.USER,
            is_verified=False,
            verification_token="expired-token-abc",
            token_expires_at=datetime.utcnow() - timedelta(minutes=10),  # already expired
        )
        db_session.add(expired_user)
        db_session.commit()

        success = AuthService.verify_email(db_session, "expired-token-abc")
        assert success is False


# ===========================================================================
# Lookup Helper Tests
# ===========================================================================

class TestUserLookups:
    def test_get_user_by_id_found(self, db_session, plain_user):
        found = AuthService.get_user_by_id(db_session, plain_user.id)
        assert found is not None
        assert found.email == plain_user.email

    def test_get_user_by_id_not_found(self, db_session):
        found = AuthService.get_user_by_id(db_session, 999999)
        assert found is None

    def test_get_user_by_email_found(self, db_session, plain_user):
        found = AuthService.get_user_by_email(db_session, plain_user.email)
        assert found is not None
        assert found.id == plain_user.id

    def test_get_user_by_email_not_found(self, db_session):
        found = AuthService.get_user_by_email(db_session, "nobody@nowhere.com")
        assert found is None


# ===========================================================================
# Admin User Tests
# ===========================================================================

class TestCreateAdminUser:
    def test_create_admin_user_when_not_exists(self, db_session):
        from app.config import settings
        # Remove any existing admin first
        existing = db_session.query(User).filter(User.email == settings.admin_email).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        admin = AuthService.create_admin_user(db_session)
        assert admin is not None
        assert admin.role == UserRole.ADMIN
        assert admin.is_verified is True

    def test_create_admin_user_returns_none_if_exists(self, db_session, admin_user):
        """Calling create_admin_user a second time (with admin already present) returns None."""
        from app.config import settings
        # Ensure the admin_user fixture email matches settings.admin_email for this test
        # We point settings admin to this fixture user to simulate already existing
        original_email = settings.admin_email
        settings.admin_email = admin_user.email
        result = AuthService.create_admin_user(db_session)
        settings.admin_email = original_email
        assert result is None
