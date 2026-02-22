"""
Integration tests for app/api/auth_routes.py

Covers:
- POST /auth/signup  (success, duplicate email, short password)
- POST /auth/signin  (success, wrong password, unverified, inactive)
- GET  /auth/me      (authenticated, unauthenticated)
- GET  /auth/verify  (valid token)
- POST /auth/verify-email/{token}  (valid, invalid)
- POST /auth/forgot-password (existing, non-existing email)
- POST /auth/verify-otp  (valid, invalid, expired)
- POST /auth/reset-password (success, invalid OTP)
- PUT  /auth/username (success, same name, requires auth)
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.database.models import User, UserRole
from app.services.auth_service import AuthService


# ===========================================================================
# Signup Tests
# ===========================================================================

class TestSignup:
    def test_signup_success(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"

    def test_signup_duplicate_email_returns_400(self, test_client):
        payload = {
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "password123",
        }
        test_client.post("/auth/signup", json=payload)
        resp = test_client.post("/auth/signup", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_signup_short_password_returns_422(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "username": "shortpassuser",
            "email": "shortpass@example.com",
            "password": "abc",       # less than 6 chars
        })
        assert resp.status_code == 422

    def test_signup_missing_email_returns_422(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "username": "nomail",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_signup_invalid_email_returns_422(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "username": "bademail",
            "email": "not-an-email",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_signup_short_username_returns_422(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "username": "ab",
            "email": "shortname@example.com",
            "password": "password123",
        })
        assert resp.status_code == 422


# ===========================================================================
# Signin Tests
# ===========================================================================

class TestSignin:
    def test_signin_success(self, test_client, plain_user):
        resp = test_client.post("/auth/signin", json={
            "email": plain_user.email,
            "password": "testpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == plain_user.email

    def test_signin_wrong_password_returns_401(self, test_client, plain_user):
        resp = test_client.post("/auth/signin", json={
            "email": plain_user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_signin_nonexistent_email_returns_401(self, test_client):
        resp = test_client.post("/auth/signin", json={
            "email": "nobody@nowhere.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_signin_unverified_user_returns_403(self, test_client, unverified_user):
        resp = test_client.post("/auth/signin", json={
            "email": unverified_user.email,
            "password": "password123",
        })
        assert resp.status_code == 403
        assert "verified" in resp.json()["detail"].lower()

    def test_signin_inactive_user_returns_401(self, test_client, inactive_user):
        resp = test_client.post("/auth/signin", json={
            "email": inactive_user.email,
            "password": "password123",
        })
        assert resp.status_code == 401


# ===========================================================================
# Get Current User Tests  (/auth/me)
# ===========================================================================

class TestGetMe:
    def test_get_me_authenticated(self, test_client, plain_user, auth_headers):
        resp = test_client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == plain_user.email
        assert data["username"] == plain_user.username

    def test_get_me_unauthenticated_returns_403(self, test_client):
        resp = test_client.get("/auth/me")
        assert resp.status_code in (401, 403)

    def test_get_me_invalid_token_returns_401_or_403(self, test_client):
        resp = test_client.get(
            "/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code in (401, 403)


# ===========================================================================
# Token Verify Tests  (/auth/verify)
# ===========================================================================

class TestVerifyToken:
    def test_verify_valid_token(self, test_client, plain_user, auth_headers):
        resp = test_client.get("/auth/verify", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["user_id"] == plain_user.id

    def test_verify_no_token_returns_403(self, test_client):
        resp = test_client.get("/auth/verify")
        assert resp.status_code in (401, 403)


# ===========================================================================
# Email Verification Tests  (POST /auth/verify-email/{token})
# ===========================================================================

class TestEmailVerification:
    def test_verify_email_valid_token(self, test_client, unverified_user):
        resp = test_client.post(f"/auth/verify-email/{unverified_user.verification_token}")
        assert resp.status_code == 200
        assert "verified" in resp.json()["message"].lower()

    def test_verify_email_invalid_token_returns_400(self, test_client):
        resp = test_client.post("/auth/verify-email/totally-wrong-token-xyz")
        assert resp.status_code == 400


# ===========================================================================
# Forgot Password Tests  (POST /auth/forgot-password)
# ===========================================================================

class TestForgotPassword:
    def test_forgot_password_existing_email(self, test_client, plain_user):
        with patch("app.services.email_service.email_service.send_password_reset_otp", return_value=True):
            resp = test_client.post("/auth/forgot-password", json={"email": plain_user.email})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_forgot_password_nonexistent_email_still_200(self, test_client):
        """Security: should not reveal whether email exists."""
        resp = test_client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
        assert resp.status_code == 200

    def test_forgot_password_invalid_email_returns_422(self, test_client):
        resp = test_client.post("/auth/forgot-password", json={"email": "not-valid"})
        assert resp.status_code == 422


# ===========================================================================
# Verify OTP Tests  (POST /auth/verify-otp)
# ===========================================================================

class TestVerifyOtp:
    def _create_otp_user(self, db_session, otp="123456", expired=False):
        hashed_pw = AuthService.hash_password("password123")
        user = User(
            username="otpuser",
            email="otpuser@example.com",
            hashed_password=hashed_pw,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            verification_token="some-token",
            token_expires_at=datetime.utcnow() + timedelta(minutes=30),
            reset_otp=otp,
            reset_otp_expires_at=(
                datetime.utcnow() - timedelta(minutes=5)
                if expired
                else datetime.utcnow() + timedelta(minutes=10)
            ),
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_verify_otp_valid(self, test_client, db_session):
        self._create_otp_user(db_session, otp="654321")
        resp = test_client.post("/auth/verify-otp", json={
            "email": "otpuser@example.com",
            "otp": "654321",
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_verify_otp_wrong_otp_returns_400(self, test_client, db_session):
        self._create_otp_user(db_session, otp="999999")
        resp = test_client.post("/auth/verify-otp", json={
            "email": "otpuser@example.com",
            "otp": "000000",
        })
        assert resp.status_code == 400

    def test_verify_otp_expired_returns_400(self, test_client, db_session):
        self._create_otp_user(db_session, otp="111111", expired=True)
        resp = test_client.post("/auth/verify-otp", json={
            "email": "otpuser@example.com",
            "otp": "111111",
        })
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    def test_verify_otp_nonexistent_email_returns_400(self, test_client):
        resp = test_client.post("/auth/verify-otp", json={
            "email": "notexists@example.com",
            "otp": "123456",
        })
        assert resp.status_code == 400


# ===========================================================================
# Reset Password Tests  (POST /auth/reset-password)
# ===========================================================================

class TestResetPassword:
    def _setup_reset_user(self, db_session):
        hashed_pw = AuthService.hash_password("oldpassword")
        user = User(
            username="resetpwuser",
            email="resetpw@example.com",
            hashed_password=hashed_pw,
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            reset_otp="777777",
            reset_otp_expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_reset_password_success(self, test_client, db_session):
        self._setup_reset_user(db_session)
        resp = test_client.post("/auth/reset-password", json={
            "email": "resetpw@example.com",
            "otp": "777777",
            "new_password": "newpassword123",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_reset_password_wrong_otp_returns_400(self, test_client, db_session):
        self._setup_reset_user(db_session)
        resp = test_client.post("/auth/reset-password", json={
            "email": "resetpw@example.com",
            "otp": "000000",
            "new_password": "newpassword123",
        })
        assert resp.status_code == 400

    def test_reset_password_short_new_password_422(self, test_client, db_session):
        self._setup_reset_user(db_session)
        resp = test_client.post("/auth/reset-password", json={
            "email": "resetpw@example.com",
            "otp": "777777",
            "new_password": "abc",  # too short
        })
        assert resp.status_code == 422


# ===========================================================================
# Update Username Tests  (PUT /auth/username)
# ===========================================================================

class TestUpdateUsername:
    def test_update_username_success(self, test_client, auth_headers):
        resp = test_client.put(
            "/auth/username",
            json={"new_username": "brandnewname"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "brandnewname"

    def test_update_username_same_name_returns_400(self, test_client, plain_user, auth_headers):
        resp = test_client.put(
            "/auth/username",
            json={"new_username": plain_user.username},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_update_username_unauthenticated_returns_403(self, test_client):
        resp = test_client.put("/auth/username", json={"new_username": "anyname"})
        assert resp.status_code in (401, 403)

    def test_update_username_too_short_returns_422(self, test_client, auth_headers):
        resp = test_client.put(
            "/auth/username",
            json={"new_username": "ab"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
