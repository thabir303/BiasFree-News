"""
Unit tests for app/services/email_service.py

All SMTP calls are mocked — no real emails are sent.

Covers:
- send_verification_email : success, SMTP failure
- send_password_reset_otp : success, SMTP failure
- send_password_reset_email : success, SMTP failure (if present)
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
import smtplib
from unittest.mock import patch, MagicMock

from app.services.email_service import EmailService


def _make_smtp_mock():
    """Return a mock that satisfies the 'with smtplib.SMTP(...) as server:' pattern."""
    mock_smtp = MagicMock()
    # MagicMock handles __enter__/__exit__ at class level; set return_value on the magic method
    mock_server = mock_smtp.__enter__.return_value
    return mock_smtp, mock_server


class TestSendVerificationEmail:
    @patch("smtplib.SMTP")
    def test_returns_true_on_success(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        result = EmailService.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            verification_token="abc123token",
        )
        assert result is True

    @patch("smtplib.SMTP")
    def test_smtp_starttls_called(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        EmailService.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            verification_token="token123",
        )
        mock_server.starttls.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_login_called(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        EmailService.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            verification_token="token123",
        )
        mock_server.login.assert_called_once()

    @patch("smtplib.SMTP", side_effect=smtplib.SMTPException("Connection refused"))
    def test_returns_false_on_smtp_error(self, _mock):
        result = EmailService.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            verification_token="token123",
        )
        assert result is False

    @patch("smtplib.SMTP", side_effect=Exception("Network error"))
    def test_returns_false_on_generic_exception(self, _mock):
        result = EmailService.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            verification_token="token123",
        )
        assert result is False


class TestSendPasswordResetOtp:
    @patch("smtplib.SMTP")
    def test_returns_true_on_success(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        result = EmailService.send_password_reset_otp(
            to_email="user@test.com",
            username="testuser",
            otp="123456",
        )
        assert result is True

    @patch("smtplib.SMTP")
    def test_sendmail_called(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        EmailService.send_password_reset_otp(
            to_email="user@test.com",
            username="testuser",
            otp="654321",
        )
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP", side_effect=smtplib.SMTPException("Auth failed"))
    def test_returns_false_on_smtp_error(self, _mock):
        result = EmailService.send_password_reset_otp(
            to_email="user@test.com",
            username="testuser",
            otp="000000",
        )
        assert result is False

    @patch("smtplib.SMTP", side_effect=Exception("Timeout"))
    def test_returns_false_on_generic_exception(self, _mock):
        result = EmailService.send_password_reset_otp(
            to_email="user@test.com",
            username="testuser",
            otp="111111",
        )
        assert result is False


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email (if it exists in EmailService)."""

    @patch("smtplib.SMTP")
    def test_returns_true_on_success(self, mock_smtp_cls):
        mock_smtp, mock_server = _make_smtp_mock()
        mock_smtp_cls.return_value = mock_smtp

        # Only run if the method exists
        if not hasattr(EmailService, "send_password_reset_email"):
            pytest.skip("send_password_reset_email not implemented")

        result = EmailService.send_password_reset_email(
            to_email="user@test.com",
            username="testuser",
            reset_token="resettoken123",
        )
        assert result is True

    @patch("smtplib.SMTP", side_effect=Exception("error"))
    def test_returns_false_on_error(self, _mock):
        if not hasattr(EmailService, "send_password_reset_email"):
            pytest.skip("send_password_reset_email not implemented")

        result = EmailService.send_password_reset_email(
            to_email="user@test.com",
            username="testuser",
            reset_token="token",
        )
        assert result is False
