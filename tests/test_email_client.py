    """
Tests for email_client.py — GuerrillaMailClient.

Uses the 'responses' library to mock HTTP calls without
hitting the real Guerrilla Mail API.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import responses as responses_lib  # avoid name collision with module

from WFChessReviewerTdev.email_client import (
    GuerrillaMailClient,
    GuerrillaMailError,
)


MOCK_API_URL = "https://api.guerrillamail.com/ajax.php"

# Realistic mock API responses
MOCK_EMAIL_RESPONSE = {
    "email_addr": "testuser@grr.la",
    "email_timestamp": 1700000000,
    "alias": "testuser",
    "sid_token": "mocksessiontoken123",
    "site": "grr.la",
    "ref_mid": "0",
    "mail_id": "0",
    "ip": "1.2.3.4",
    "lang": "en",
    "auth": {"success": True, "error_codes": []},
}

MOCK_EMAIL_LIST_WITH_MAIL = {
    "list": [
        {
            "mail_id": "12345",
            "mail_from": "noreply@chess.com",
            "mail_subject": "Please verify your Chess.com account",
            "mail_timestamp": "1700000100",
            "mail_read": "0",
            "mail_expt": "testuser@grr.la",
            "mail_excerpt": "Click here to verify...",
            "att": "0",
        }
    ],
    "count": "1",
    "email": "testuser@grr.la",
    "alias": "testuser",
    "ts": 1700000100,
    "sid_token": "mocksessiontoken123",
}

MOCK_EMAIL_LIST_EMPTY = {
    "list": [],
    "count": "0",
    "email": "testuser@grr.la",
}

MOCK_EMAIL_BODY_RESPONSE = {
    "mail_id": "12345",
    "mail_body": (
        '<html><body>Click here to verify: '
        '<a href="https://www.chess.com/callback/email-verification/abc123">'
        'Verify Email</a></body></html>'
    ),
    "mail_from": "noreply@chess.com",
    "mail_subject": "Please verify your Chess.com account",
    "mail_timestamp": "1700000100",
}


class TestGuerrillaMailClientInit:
    """Tests for client initialization."""

    def test_default_api_url(self) -> None:
        """Client uses the config API URL by default."""
        client = GuerrillaMailClient()
        assert "guerrillamail.com" in client._api_url
        client.close()

    def test_custom_api_url(self) -> None:
        """Client accepts a custom API URL."""
        client = GuerrillaMailClient(api_url="https://custom.api.com/ajax.php")
        assert client._api_url == "https://custom.api.com/ajax.php"
        client.close()

    def test_context_manager(self) -> None:
        """Client can be used as a context manager."""
        with GuerrillaMailClient() as client:
            assert client._session is not None
        # Session should be closed after exit
        assert client._session.adapters == {}  # closed sessions have empty adapters


class TestGetEmailAddress:
    """Tests for get_email_address()."""

    @responses_lib.activate
    def test_get_email_success(self) -> None:
        """Returns email and token on successful API response."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_RESPONSE,
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        email, token = client.get_email_address()

        assert email == "testuser@grr.la"
        assert token == "mocksessiontoken123"
        client.close()

    @responses_lib.activate
    def test_get_email_missing_email_addr(self) -> None:
        """Raises GuerrillaMailError if email_addr is missing from response."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json={"sid_token": "token123"},  # Missing email_addr
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        with pytest.raises(GuerrillaMailError, match="missing email_addr"):
            client.get_email_address()
        client.close()

    @responses_lib.activate
    def test_get_email_http_error(self) -> None:
        """Raises GuerrillaMailError on HTTP 500 response."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            status=500,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        with pytest.raises(GuerrillaMailError, match="HTTP error 500"):
            client.get_email_address()
        client.close()


class TestCheckInbox:
    """Tests for check_inbox()."""

    @responses_lib.activate
    def test_inbox_with_emails(self) -> None:
        """Returns email list when inbox has messages."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_LIST_WITH_MAIL,
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        emails = client.check_inbox("mocksessiontoken123")

        assert len(emails) == 1
        assert emails[0]["mail_id"] == "12345"
        assert "chess.com" in emails[0]["mail_from"]
        client.close()

    @responses_lib.activate
    def test_inbox_empty(self) -> None:
        """Returns empty list when inbox has no messages."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_LIST_EMPTY,
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        emails = client.check_inbox("mocksessiontoken123")
        assert emails == []
        client.close()

    @responses_lib.activate
    def test_inbox_api_failure_returns_empty(self) -> None:
        """Returns empty list (instead of raising) on API failure."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            status=503,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        # Should not raise — should return empty list
        emails = client.check_inbox("token")
        assert emails == []
        client.close()


class TestGetEmailBody:
    """Tests for get_email_body()."""

    @responses_lib.activate
    def test_fetch_email_body_success(self) -> None:
        """Returns HTML body on successful fetch."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_BODY_RESPONSE,
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        body = client.get_email_body("token123", "12345")

        assert body is not None
        assert "chess.com" in body
        assert "verify" in body.lower()
        client.close()

    @responses_lib.activate
    def test_fetch_email_body_none_on_failure(self) -> None:
        """Returns None when API fails to return a body."""
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json={"mail_body": ""},
            status=200,
        )
        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        body = client.get_email_body("token123", "12345")
        assert body is None
        client.close()


class TestWaitForEmailFrom:
    """Tests for wait_for_email_from() polling logic."""

    @responses_lib.activate
    def test_finds_chess_email_on_first_poll(self) -> None:
        """Returns (mail_id, body) when Chess.com email is present on first poll."""
        # First call: check_inbox
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_LIST_WITH_MAIL,
            status=200,
        )
        # Second call: get_email_body
        responses_lib.add(
            responses_lib.GET,
            MOCK_API_URL,
            json=MOCK_EMAIL_BODY_RESPONSE,
            status=200,
        )

        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        result = client.wait_for_email_from(
            session_token="token",
            sender_keyword="chess.com",
            poll_interval=0.01,  # Near-instant for tests
            max_attempts=3,
        )

        assert result is not None
        mail_id, body = result
        assert mail_id == "12345"
        assert body is not None
        client.close()

    @responses_lib.activate
    def test_returns_none_after_max_attempts(self) -> None:
        """Returns None if no email arrives within max_attempts."""
        # Always return empty inbox
        for _ in range(5):
            responses_lib.add(
                responses_lib.GET,
                MOCK_API_URL,
                json=MOCK_EMAIL_LIST_EMPTY,
                status=200,
            )

        client = GuerrillaMailClient(api_url=MOCK_API_URL)
        result = client.wait_for_email_from(
            session_token="token",
            sender_keyword="chess.com",
            poll_interval=0.01,
            max_attempts=5,
        )

        assert result is None
        client.close()