"""
config.py — Application Configuration
======================================
Loads environment variables from .env file and provides
a strongly-typed configuration object used across the application.

All settings have sensible defaults so the app works out-of-the-box
even without a .env file present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# Resolve project root directory (3 levels up from this file)
# src/WFChessReviewerTdev/config.py  →  project root
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_PACKAGE_DIR = _THIS_FILE.parent  # src/WFChessReviewerTdev/
_SRC_DIR = _PACKAGE_DIR.parent  # src/
PROJECT_ROOT = _SRC_DIR.parent  # WFChessReviewerTdev/

# Load .env from project root (silently if absent)
_ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH, override=False)


def _env_bool(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable (true/yes/1 → True)."""
    raw = os.getenv(key, str(default)).strip().lower()
    return raw in {"true", "yes", "1", "on"}


def _env_int(key: str, default: int) -> int:
    """Parse an integer environment variable with fallback."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid integer value for {key!r}, using default {default}")
        return default


def _env_float(key: str, default: float) -> float:
    """Parse a float environment variable with fallback."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid float value for {key!r}, using default {default}")
        return default


@dataclass
class AppConfig:
    """
    Central configuration dataclass.

    All attributes correspond to environment variables documented
    in .env.example. Each attribute has a sane default value.

    Attributes
    ----------
    browser_headless : bool
        Run Playwright browser in headless mode (no visible window).
    slow_mo : int
        Slow-motion delay in milliseconds applied to Playwright actions.
    default_timeout : int
        Default element wait timeout in milliseconds.
    navigation_timeout : int
        Page navigation timeout in milliseconds.
    email_poll_interval : float
        Seconds between Guerrilla Mail inbox polling attempts.
    email_poll_max_attempts : int
        Maximum number of polling attempts before giving up.
    log_level : str
        Loguru log level (DEBUG / INFO / WARNING / ERROR).
    screenshots_dir : Path
        Directory where debug screenshots are saved.
    logs_dir : Path
        Directory where rotating log files are saved.
    credentials_dir : Path
        Directory where credential JSON files are saved.
    assets_dir : Path
        Directory containing static assets (icon, etc.).
    guerrilla_api_url : str
        Base URL for the Guerrilla Mail REST API.
    chess_register_url : str
        Chess.com registration page URL.
    """

    # --- Browser settings ---
    browser_headless: bool = field(
        default_factory=lambda: _env_bool("BROWSER_HEADLESS", False)
    )
    slow_mo: int = field(default_factory=lambda: _env_int("SLOW_MO", 50))
    default_timeout: int = field(
        default_factory=lambda: _env_int("DEFAULT_TIMEOUT", 30_000)
    )
    navigation_timeout: int = field(
        default_factory=lambda: _env_int("NAVIGATION_TIMEOUT", 60_000)
    )

    # --- Email polling settings ---
    email_poll_interval: float = field(
        default_factory=lambda: _env_float("EMAIL_POLL_INTERVAL", 5.0)
    )
    email_poll_max_attempts: int = field(
        default_factory=lambda: _env_int("EMAIL_POLL_MAX_ATTEMPTS", 60)
    )

    # --- Logging ---
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )

    # --- Paths (computed from project root) ---
    screenshots_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "screenshots")
    logs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")
    credentials_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "credentials")
    assets_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "assets")

    # --- External URLs ---
    guerrilla_api_url: str = "https://api.guerrillamail.com/ajax.php"
    chess_register_url: str = "https://www.chess.com/register"
    chess_login_url: str = "https://www.chess.com/login"

    def __post_init__(self) -> None:
        """Ensure all required directories exist after instantiation."""
        for directory in (
            self.screenshots_dir,
            self.logs_dir,
            self.credentials_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> "AppConfig":
        """
        Factory method: reload .env and return a fresh AppConfig instance.

        Returns
        -------
        AppConfig
            Freshly loaded configuration instance.
        """
        load_dotenv(_ENV_PATH, override=True)
        return cls()

    def icon_path(self) -> Optional[Path]:
        """
        Return path to app icon if it exists, else None.

        Returns
        -------
        Optional[Path]
            Path to icon.png or None.
        """
        candidate = self.assets_dir / "icon.png"
        return candidate if candidate.exists() else None


# Module-level singleton — import this in other modules
config: AppConfig = AppConfig.load()
