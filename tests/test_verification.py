"""
Tests for verification.py — VerificationExtractor.

Tests all four extraction strategies with realistic email bodies.
"""

from __future__ import annotations

import pytest

from WFChessReviewerTdev.verification import VerificationExtractor, VerificationResult

# ── Sample email bodies ───────────────────────────────────────────────────────

HTML_WITH_VERIFICATION_LINK = """
<html>
<body>
<h1>Welcome to Chess.com!</h1>
<p>Please verify your email address by clicking the link below:</p>
<a href="https://www.chess.com/callback/email-verification/abc123def456">
  Verify Email Address
</a>
<p>If you didn't create an account, ignore this email.</p>
</body>
</html>
"""

HTML_WITH_CONFIRM_LINK = """
<html>
<body>
<p>Confirm your account:</p>
<a href="https://secure.chess.com/confirm/email?token=xyz789">Click here</a>
</body>
</html>
"""

HTML_WITH_UNRELATED_LINKS = """
<html>
<body>
<a href="https://google.com/something">Not relevant</a>
<a href="https://www.chess.com/home">Chess Home</a>
</body>
</html>
"""

HTML_WITH_OTP_NEAR_KEYWORD = """
<html>
<body>
<p>Your verification code is: <strong>847291</strong></p>
<p>Enter this code in the app within 10 minutes.</p>
</body>
</html>
"""

HTML_WITH_STANDALONE_OTP = """
<html>
<body>
<p>Use this code to confirm your identity: 5638</p>
</body>
</html>
"""

PLAIN_TEXT_WITH_URL = """
Hello,
Please verify your account by visiting:
https://www.chess.com/callback/email-verification/tokenhere
Thank you.
"""

EMPTY_BODY = ""

HTML_NO_CHESS_LINKS = """
<html><body><a href="https://example.com">Example</a></body></html>
"""


class TestVerificationExtractor:
    """Tests for all four extraction strategies."""

    def setup_method(self) -> None:
        """Create a fresh extractor for each test."""
        self.extractor = VerificationExtractor()

    # ── Strategy 1: HTML link with keyword ───────────────────────────

    def test_strategy1_keyword_link(self) -> None:
        """Finds verification link with keyword match in chess.com anchor."""
        result = self.extractor.extract(HTML_WITH_VERIFICATION_LINK)

        assert result.has_link
        assert "chess.com" in result.verification_link
        assert "verification" in result.verification_link
        assert not result.has_otp

    def test_strategy1_confirm_link(self) -> None:
        """Finds confirm-keyword link in chess.com anchor."""
        result = self.extractor.extract(HTML_WITH_CONFIRM_LINK)

        assert result.has_link
        assert "chess.com" in result.verification_link
        assert "confirm" in result.verification_link

    # ── Strategy 2: Any chess.com link ────────────────────────────────

    def test_strategy2_any_chess_link(self) -> None:
        """Falls back to any chess.com link when no keyword match."""
        result = self.extractor.extract(HTML_WITH_UNRELATED_LINKS)

        # Should pick chess.com link (not google.com)
        assert result.has_link
        assert "chess.com" in result.verification_link

    # ── Strategy 3: Regex URL in plain text ──────────────────────────

    def test_strategy3_regex_url_in_plaintext(self) -> None:
        """Finds chess.com URL via regex in plain text email."""
        result = self.extractor.extract(PLAIN_TEXT_WITH_URL)

        assert result.has_link
        assert "chess.com" in result.verification_link
        assert "verification" in result.verification_link

    # ── Strategy 4: OTP extraction ────────────────────────────────────

    def test_strategy4_otp_near_keyword(self) -> None:
        """Extracts OTP code when near 'verification code' keyword."""
        result = self.extractor.extract(HTML_WITH_OTP_NEAR_KEYWORD)

        assert result.has_otp
        assert result.otp_code == "847291"
        assert not result.has_link

    def test_strategy4_standalone_otp(self) -> None:
        """Extracts standalone 4-digit OTP code."""
        result = self.extractor.extract(HTML_WITH_STANDALONE_OTP)

        assert result.has_otp
        assert result.otp_code == "5638"

    # ── Edge cases ────────────────────────────────────────────────────

    def test_empty_body_returns_no_result(self) -> None:
        """Empty email body returns VerificationResult with nothing found."""
        result = self.extractor.extract(EMPTY_BODY)

        assert not result.has_link
        assert not result.has_otp
        assert not result.found_anything

    def test_no_chess_links_no_otp(self) -> None:
        """HTML without chess.com links or OTP returns empty result."""
        result = self.extractor.extract(HTML_NO_CHESS_LINKS)

        assert not result.has_link
        assert not result.has_otp

    def test_raw_links_populated(self) -> None:
        """raw_links is populated when chess.com links are found."""
        result = self.extractor.extract(HTML_WITH_VERIFICATION_LINK)

        assert isinstance(result.raw_links, list)
        assert len(result.raw_links) >= 1

    def test_raw_links_empty_when_none_found(self) -> None:
        """raw_links is empty list when no chess.com links found."""
        result = self.extractor.extract(HTML_NO_CHESS_LINKS)
        assert result.raw_links == []

    def test_found_anything_property(self) -> None:
        """found_anything is True when either link or OTP is found."""
        result_with_link = self.extractor.extract(HTML_WITH_VERIFICATION_LINK)
        result_empty = self.extractor.extract(EMPTY_BODY)

        assert result_with_link.found_anything
        assert not result_empty.found_anything

    def test_non_chess_links_ignored(self) -> None:
        """google.com links in HTML are not returned as verification links."""
        html = '<a href="https://google.com/verify?token=abc">Click</a>'
        result = self.extractor.extract(html)
        assert not result.has_link

    def test_year_not_extracted_as_otp(self) -> None:
        """4-digit years like 2024 are filtered out as OTP candidates."""
        html = "<p>Copyright 2024. All rights reserved.</p>"
        result = self.extractor.extract(html)
        # 2024 should be filtered as it's a year
        assert not result.has_otp

    def test_chess_subdomain_link_accepted(self) -> None:
        """Links on chess.com subdomains are accepted."""
        html = '<a href="https://account.chess.com/verify?t=abc123">' "Verify</a>"
        result = self.extractor.extract(html)
        assert result.has_link
        assert "chess.com" in result.verification_link
