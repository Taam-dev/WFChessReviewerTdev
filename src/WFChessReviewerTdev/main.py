#!/usr/bin/env python3
"""
Entry point for Chess Auto Viewer.

Usage:
    python -m chess_auto_viewer
    chess-auto-viewer                         # if installed via pip
    chess-auto-viewer --url <url>             # skip interactive prompt
    chess-auto-viewer --headless --url <url>  # run without a visible browser
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

from loguru import logger

from .automator import ChessComAutomator
from .config import CONFIG, LOGS_DIR

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{function}</cyan> — "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
    )
    logger.add(
        str(LOGS_DIR / "chess_auto_{time}.log"),
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

_VALID_URL_PATTERNS = [
    r"^https?://(?:www\.)?chess\.com/member/[\w-]+/games",
    r"^https?://(?:www\.)?chess\.com/games/archive/[\w-]+",
    r"^https?://(?:www\.)?chess\.com/game/[\w-]+",
    r"^https?://(?:www\.)?chess\.com/[\w/\-?=&]+",
]


def validate_chess_url(url: str) -> bool:
    """Return True if *url* looks like a valid Chess.com URL."""
    return bool(url) and any(
        re.match(pattern, url.strip()) for pattern in _VALID_URL_PATTERNS
    )


def prompt_for_url() -> str:
    """Interactively ask the user for a Chess.com history URL."""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║   Chess.com Auto-Registration & Match History Viewer   ║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("  This tool will:")
    print("    1. Generate a temporary email address")
    print("    2. Create a new Chess.com account")
    print("    3. Verify the email (if required)")
    print("    4. Open your specified match history URL")
    print()
    print("  Example URLs:")
    print("    https://www.chess.com/member/hikaru/games")
    print("    https://www.chess.com/member/magnuscarlsen/games")
    print("    https://www.chess.com/games/archive/hikaru")
    print()

    while True:
        url = input("  ▶  Enter Chess.com URL: ").strip()
        if validate_chess_url(url):
            print(f"\n  ✓ URL accepted: {url}\n")
            return url
        print("  ✗ Invalid URL — must start with https://www.chess.com/\n")


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-auto-viewer",
        description="Auto-register on Chess.com and view a match history page.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  chess-auto-viewer
  chess-auto-viewer --url https://www.chess.com/member/hikaru/games
  chess-auto-viewer --url https://www.chess.com/member/hikaru/games --headless
  chess-auto-viewer --url https://www.chess.com/member/hikaru/games --log-level DEBUG
        """,
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="Chess.com match history URL (skips interactive prompt)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (no visible window)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=CONFIG["log_level"],
        metavar="LEVEL",
        help="Logging verbosity (default: %(default)s)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="chess-auto-viewer 1.0.0",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main() -> int:
    """Async entry point. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args()

    _configure_logging(args.log_level)

    # Honour --headless CLI flag
    if args.headless:
        CONFIG["browser_headless"] = True
        logger.info("Headless mode enabled")

    # Resolve target URL
    if args.url:
        if not validate_chess_url(args.url):
            logger.error(f"Invalid URL: {args.url}")
            return 1
        target_url = args.url
    else:
        target_url = prompt_for_url()

    automator = ChessComAutomator(target_url)
    await automator.run()
    return 0


def main() -> None:
    """Synchronous wrapper used by the console_scripts entry point."""
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n  Exiting — goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
