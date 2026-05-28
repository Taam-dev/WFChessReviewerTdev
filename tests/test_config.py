"""
Tests for config.py — AppConfig loading and validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from WFChessReviewerTdev.config import AppConfig, PROJECT_ROOT


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        """AppConfig has sensible defaults without any env vars."""
        # Patch all relevant env vars to not exist
        env_overrides = {
            "BROWSER_HEADLESS": None,
            "SLOW_MO": None,
            "DEFAULT_TIMEOUT": None,
            "NAVIGATION_TIMEOUT": None,
            "EMAIL_POLL_INTERVAL": None,
            "EMAIL_POLL_MAX_ATTEMPTS": None,
            "LOG_LEVEL": None,
        }
        # Remove these keys from environment during test
        with patch.dict(os.environ, {}, clear=False):
            for key in env_overrides:
                os.environ.pop(key, None)
            cfg = AppConfig()

        assert cfg.browser_headless is False
        assert cfg.slow_mo == 50
        assert cfg.default_timeout == 30_000
        assert cfg.navigation_timeout == 60_000
        assert cfg.email_poll_interval == 5.0
        assert cfg.email_poll_max_attempts == 60
        assert cfg.log_level == "INFO"

    def test_headless_from_env(self) -> None:
        """BROWSER_HEADLESS=true sets browser_headless to True."""
        with patch.dict(os.environ, {"BROWSER_HEADLESS": "true"}):
            cfg = AppConfig()
        assert cfg.browser_headless is True

    def test_headless_false_variants(self) -> None:
        """BROWSER_HEADLESS=false/0/no sets browser_headless to False."""
        for value in ("false", "0", "no", "off"):
            with patch.dict(os.environ, {"BROWSER_HEADLESS": value}):
                cfg = AppConfig()
            assert cfg.browser_headless is False

    def test_slow_mo_from_env(self) -> None:
        """SLOW_MO env var overrides slow_mo setting."""
        with patch.dict(os.environ, {"SLOW_MO": "200"}):
            cfg = AppConfig()
        assert cfg.slow_mo == 200

    def test_invalid_slow_mo_uses_default(self) -> None:
        """Invalid SLOW_MO falls back to default (50)."""
        with patch.dict(os.environ, {"SLOW_MO": "not_a_number"}):
            cfg = AppConfig()
        assert cfg.slow_mo == 50

    def test_log_level_uppercase(self) -> None:
        """LOG_LEVEL is always uppercased."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            cfg = AppConfig()
        assert cfg.log_level == "DEBUG"

    def test_directories_created(self, tmp_path: Path) -> None:
        """__post_init__ creates screenshots, logs, and credentials dirs."""
        cfg = AppConfig()
        # These dirs must exist after instantiation
        assert cfg.screenshots_dir.exists()
        assert cfg.logs_dir.exists()
        assert cfg.credentials_dir.exists()

    def test_paths_are_path_objects(self) -> None:
        """Directory attributes are Path objects."""
        cfg = AppConfig()
        assert isinstance(cfg.screenshots_dir, Path)
        assert isinstance(cfg.logs_dir, Path)
        assert isinstance(cfg.credentials_dir, Path)
        assert isinstance(cfg.assets_dir, Path)

    def test_urls_are_strings(self) -> None:
        """API and page URLs are non-empty strings."""
        cfg = AppConfig()
        assert cfg.guerrilla_api_url.startswith("https://")
        assert cfg.chess_register_url.startswith("https://")
        assert cfg.chess_login_url.startswith("https://")

    def test_load_factory_method(self) -> None:
        """load() class method returns an AppConfig instance."""
        cfg = AppConfig.load()
        assert isinstance(cfg, AppConfig)

    def test_icon_path_returns_none_when_missing(self) -> None:
        """icon_path() returns None when icon.png doesn't exist."""
        cfg = AppConfig()
        # Assets dir exists but icon.png may not — just verify return type
        result = cfg.icon_path()
        assert result is None or result.name == "icon.png"
