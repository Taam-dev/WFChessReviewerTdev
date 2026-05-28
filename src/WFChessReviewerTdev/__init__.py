"""
WFChessReviewerTdev — Chess.com Account Automation & Review Tool
================================================================
A desktop GUI application that automates:
  - Temporary email generation via Guerrilla Mail API
  - Chess.com account registration with stealth browser
  - Email verification handling
  - Navigation to user-specified Chess.com match history URLs

Version: 1.0.0
License: MIT
Author: WFChessReviewerTdev Contributors
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "WFChessReviewerTdev Contributors"
__license__ = "MIT"
__description__ = "Chess.com Account Automation & Review Desktop Tool"

# Public API exports
from .credentials import CredentialGenerator
from .email_client import GuerrillaMailClient
from .verification import VerificationExtractor
from .config import AppConfig

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "__description__",
    "CredentialGenerator",
    "GuerrillaMailClient",
    "VerificationExtractor",
    "AppConfig",
]
