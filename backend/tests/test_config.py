"""
Unit tests for app/config/newspapers.py

Covers:
- NewspaperConfig model validation
- get_enabled_newspapers()
- get_newspaper_config() – success and KeyError path
- get_all_newspaper_keys()
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest

from app.config.newspapers import (
    NEWSPAPER_CONFIGS,
    NewspaperConfig,
    get_enabled_newspapers,
    get_newspaper_config,
    get_all_newspaper_keys,
)


class TestNewspaperConfig:
    def test_prothom_alo_exists(self):
        assert "prothom_alo" in NEWSPAPER_CONFIGS

    def test_jugantor_exists(self):
        assert "jugantor" in NEWSPAPER_CONFIGS

    def test_daily_star_exists(self):
        assert "daily_star" in NEWSPAPER_CONFIGS

    def test_config_has_required_fields(self):
        cfg = NEWSPAPER_CONFIGS["prothom_alo"]
        assert cfg.name
        assert cfg.key == "prothom_alo"
        assert cfg.base_url.startswith("http")
        assert cfg.language in ("bengali", "english")
        assert isinstance(cfg.enabled, bool)
        assert cfg.scraper_type

    def test_all_configs_have_selectors(self):
        for key, cfg in NEWSPAPER_CONFIGS.items():
            assert isinstance(cfg.selectors, dict), f"{key} has no selectors"
            assert len(cfg.selectors) > 0

    def test_newspaper_config_model_creation(self):
        cfg = NewspaperConfig(
            name="Test Paper",
            key="test_paper",
            base_url="https://test.com",
            language="bengali",
            enabled=True,
            scraper_type="test",
            selectors={"article_list": ".item"},
        )
        assert cfg.key == "test_paper"

    def test_enabled_defaults_to_true(self):
        cfg = NewspaperConfig(
            name="Test", key="t", base_url="https://t.com",
            language="bengali", scraper_type="t", selectors={},
        )
        assert cfg.enabled is True


class TestGetEnabledNewspapers:
    def test_returns_list(self):
        result = get_enabled_newspapers()
        assert isinstance(result, list)

    def test_all_returned_are_enabled(self):
        for cfg in get_enabled_newspapers():
            assert cfg.enabled is True

    def test_returns_at_least_one_newspaper(self):
        assert len(get_enabled_newspapers()) >= 1

    def test_disabled_newspaper_excluded(self):
        """Temporarily disable one newspaper and verify it's excluded."""
        cfg = NEWSPAPER_CONFIGS["prothom_alo"]
        original = cfg.enabled
        object.__setattr__(cfg, "enabled", False)
        try:
            keys = [c.key for c in get_enabled_newspapers()]
            assert "prothom_alo" not in keys
        finally:
            object.__setattr__(cfg, "enabled", original)


class TestGetNewspaperConfig:
    def test_returns_config_for_known_key(self):
        cfg = get_newspaper_config("prothom_alo")
        assert cfg.key == "prothom_alo"

    def test_returns_jugantor_config(self):
        cfg = get_newspaper_config("jugantor")
        assert cfg.key == "jugantor"

    def test_unknown_key_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown newspaper"):
            get_newspaper_config("nonexistent_paper")

    def test_error_message_contains_key(self):
        try:
            get_newspaper_config("mystery_paper")
        except ValueError as e:
            assert "mystery_paper" in str(e)


class TestGetAllNewspaperKeys:
    def test_returns_list(self):
        assert isinstance(get_all_newspaper_keys(), list)

    def test_prothom_alo_in_keys(self):
        assert "prothom_alo" in get_all_newspaper_keys()

    def test_count_matches_configs(self):
        assert len(get_all_newspaper_keys()) == len(NEWSPAPER_CONFIGS)

    def test_all_keys_are_strings(self):
        for key in get_all_newspaper_keys():
            assert isinstance(key, str)
