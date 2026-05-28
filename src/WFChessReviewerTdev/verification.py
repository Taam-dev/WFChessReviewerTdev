"""
verification.py — Email Verification Link & OTP Extractor
==========================================================
Parses Chess.com verification emails to extract:
  1. Verification links (href URLs containing chess.com)
  2. OTP / numeric verification codes (4–8 digit patterns)

Uses BeautifulSoup for HTML parsing with multiple fallback
strategies to handle different email template formats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Chess.com domains to match in verification links
_CHESS_DOMAINS = {
    "chess.com",
    "www.chess.com",
    "secure.chess.com",
    "account.chess.com",
    "mail.chess.com",
}

# Regex patterns for verification links
_LINK_KEYWORDS = [
    "verify",
    "confirm",
    "activate",
    "validation",
    "account",
    "email",
    "register",
]

# Regex for OTP codes: 4 to 8 consecutive digits, standalone
_OTP_PATTERN = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")

# Regex fallback for any chess.com URL in raw text
_CHESS_URL_PATTERN = re.compile(
    r"https?://(?:[\w\-]+\.)?chess\.com/[\w/\-?=&%+.#]+",
    re.IGNORECASE,
)


@dataclass
class VerificationResult:
    """
    Result of parsing a verification email.

    Attributes
    ----------
    verification_link : Optional[str]
        The verification URL to navigate to, if found.
    otp_code : Optional[str]
        The numeric OTP code to enter, if found.
    raw_links : List[str]
        All chess.com links found in the email (for debugging).
    """

    verification_link: Optional[str] = None
    otp_code: Optional[str] = None
    raw_links: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.raw_links is None:
            self.raw_links = []

    @property
    def has_link(self) -> bool:
        """True if a verification link was found."""
        return self.verification_link is not None

    @property
    def has_otp(self) -> bool:
        """True if an OTP code was found."""
        return self.otp_code is not None

    @property
    def found_anything(self) -> bool:
        """True if any verification method was found."""
        return self.has_link or self.has_otp


class VerificationExtractor:
    """
    Extracts verification links and OTP codes from Chess.com emails.

    Strategy order (most reliable to least):
      1. Parse HTML anchor tags with chess.com href and link keywords
      2. Parse all chess.com anchor hrefs (any keyword)
      3. Regex search for chess.com URLs in raw text
      4. Regex search for 4-8 digit OTP codes

    Examples
    --------
    >>> extractor = VerificationExtractor()
    >>> result = extractor.extract(html_body)
    >>> if result.has_link:
    ...     browser.goto(result.verification_link)
    >>> elif result.has_otp:
    ...     otp_input.fill(result.otp_code)
    """

    def extract(self, email_body: str) -> VerificationResult:
        """
        Parse an email body and extract verification information.

        Parameters
        ----------
        email_body : str
            Raw email body (HTML or plain text).

        Returns
        -------
        VerificationResult
            Parsed verification data with link and/or OTP code.
        """
        if not email_body or not email_body.strip():
            logger.warning("Email body is empty — nothing to extract")
            return VerificationResult()

        result = VerificationResult()

        # --- Strategy 1 & 2: HTML link extraction ---
        all_chess_links = self._extract_html_links(email_body)
        result.raw_links = all_chess_links
        logger.debug(f"Found {len(all_chess_links)} chess.com link(s) in email HTML")

        # Strategy 1: Prefer links with verification-related keywords
        keyword_links = [
            link
            for link in all_chess_links
            if any(kw in link.lower() for kw in _LINK_KEYWORDS)
        ]
        if keyword_links:
            result.verification_link = keyword_links[0]
            logger.info(
                f"Strategy 1 — Verification link found (keyword match): "
                f"{result.verification_link!r}"
            )
            return result

        # Strategy 2: Any chess.com link
        if all_chess_links:
            result.verification_link = all_chess_links[0]
            logger.info(
                f"Strategy 2 — Verification link found (first chess.com href): "
                f"{result.verification_link!r}"
            )
            return result

        # --- Strategy 3: Regex search for chess.com URLs in raw content ---
        regex_links = self._extract_regex_links(email_body)
        if regex_links:
            result.raw_links.extend(regex_links)
            result.verification_link = regex_links[0]
            logger.info(
                f"Strategy 3 — Verification link found (regex URL): "
                f"{result.verification_link!r}"
            )
            return result

        # --- Strategy 4: OTP code extraction ---
        otp = self._extract_otp(email_body)
        if otp:
            result.otp_code = otp
            logger.info(f"Strategy 4 — OTP code found: {otp!r}")
            return result

        logger.warning(
            "No verification link or OTP found in email body. "
            "Manual verification may be required."
        )
        return result

    # ------------------------------------------------------------------
    # Private extraction methods
    # ------------------------------------------------------------------

    def _extract_html_links(self, html: str) -> List[str]:
        """
        Parse HTML and return all chess.com anchor hrefs.

        Parameters
        ----------
        html : str
            Raw HTML string.

        Returns
        -------
        List[str]
            List of chess.com URLs found in <a href="..."> tags.
        """
        links: List[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            anchors = soup.find_all("a", href=True)

            for anchor in anchors:
                href = str(anchor["href"]).strip()
                if not href or href.startswith(("mailto:", "tel:", "#")):
                    continue

                # Parse the URL to check the domain
                try:
                    parsed = urlparse(href)
                    hostname = parsed.hostname or ""
                    # Match exact domains or subdomains of chess.com
                    if hostname in _CHESS_DOMAINS or hostname.endswith(".chess.com"):
                        if href not in links:
                            links.append(href)
                except ValueError:
                    continue

        except Exception as exc:
            logger.debug(f"HTML link extraction error: {exc}")

        return links

    def _extract_regex_links(self, text: str) -> List[str]:
        """
        Use regex to find chess.com URLs in raw text/HTML.

        Parameters
        ----------
        text : str
            Raw text or HTML string.

        Returns
        -------
        List[str]
            List of unique chess.com URLs found via regex.
        """
        matches = _CHESS_URL_PATTERN.findall(text)
        # Deduplicate while preserving order
        seen: set = set()
        unique: List[str] = []
        for match in matches:
            # Clean trailing HTML artifacts
            clean = re.split(r'["\'\s<>]', match)[0]
            if clean and clean not in seen:
                seen.add(clean)
                unique.append(clean)
        return unique

    def _extract_otp(self, text: str) -> Optional[str]:
        """
        Search for a standalone numeric OTP code in text.

        Prefers codes that appear near verification-related words.

        Parameters
        ----------
        text : str
            Raw email text.

        Returns
        -------
        Optional[str]
            The first plausible OTP code found, or None.
        """
        # Strip HTML tags for cleaner text matching
        try:
            plain_text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
        except Exception:
            plain_text = text

        # Look for OTP near verification keywords for higher confidence
        verification_keywords_pattern = re.compile(
            r"(?:code|otp|pin|verify|verification|confirmation|one.?time)"
            r"[^\d]{0,50}(\d{4,8})",
            re.IGNORECASE | re.DOTALL,
        )
        keyword_match = verification_keywords_pattern.search(plain_text)
        if keyword_match:
            return keyword_match.group(1)

        # Fallback: any standalone 4-8 digit sequence
        all_matches = _OTP_PATTERN.findall(plain_text)
        # Filter out years and common non-OTP numbers
        filtered = [
            m for m in all_matches if not (1900 <= int(m) <= 2100 and len(m) == 4)
        ]
        return filtered[0] if filtered else None
