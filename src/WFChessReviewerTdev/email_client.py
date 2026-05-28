"""
email_client.py — Guerrilla Mail API Client
============================================
Provides a clean interface to the Guerrilla Mail REST API for:
  - Generating a temporary email address
  - Polling the inbox for new messages
  - Fetching the full body of a specific email

Guerrilla Mail API documentation:
  https://www.guerrillamail.com/GuerrillaMailAPI.html

All HTTP calls are made with requests.Session for connection reuse
and proper timeout handling.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple, Any

import requests
from loguru import logger

from .config import config


class GuerrillaMailError(Exception):
    """Raised when the Guerrilla Mail API returns an unexpected response."""

    pass


class GuerrillaMailClient:
    """
    HTTP client for the Guerrilla Mail temporary email service.

    The client maintains a session token (PHPSESSID equivalent)
    across all requests so subsequent calls retrieve the same mailbox.

    Parameters
    ----------
    api_url : str
        Base URL for the Guerrilla Mail AJAX API.
        Defaults to the value from AppConfig.

    Examples
    --------
    >>> client = GuerrillaMailClient()
    >>> email, token = client.get_email_address()
    >>> emails = client.check_inbox(token)
    >>> body = client.get_email_body(token, email_id="12345")
    """

    # Guerrilla Mail API actions
    _ACTION_GET_EMAIL = "get_email_address"
    _ACTION_GET_EMAIL_LIST = "get_email_list"
    _ACTION_FETCH_EMAIL = "fetch_email"
    _ACTION_SET_EMAIL_USER = "set_email_user"

    # HTTP request timeout in seconds
    _REQUEST_TIMEOUT = 30

    def __init__(self, api_url: Optional[str] = None) -> None:
        self._api_url = api_url or config.guerrilla_api_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.guerrillamail.com/",
            }
        )
        logger.debug(f"GuerrillaMailClient initialized with API: {self._api_url}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_email_address(self) -> Tuple[str, str]:
        """
        Request a fresh temporary email address from Guerrilla Mail.

        Returns
        -------
        Tuple[str, str]
            A 2-tuple of (email_address, session_token).
            The session_token must be passed to all subsequent calls.

        Raises
        ------
        GuerrillaMailError
            If the API call fails or returns an unexpected response.
        """
        logger.info("Requesting temporary email address from Guerrilla Mail...")

        response = self._get(
            action=self._ACTION_GET_EMAIL,
            params={"lang": "en"},
        )

        email_address = response.get("email_addr")
        session_token = response.get("sid_token")

        if not email_address or not session_token:
            raise GuerrillaMailError(
                f"API response missing email_addr or sid_token: {response}"
            )

        logger.success(f"Temporary email obtained: {email_address!r}")
        return email_address, session_token

    def check_inbox(
        self,
        session_token: str,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Poll the mailbox for a list of emails (without bodies).

        Parameters
        ----------
        session_token : str
            The session token returned by get_email_address().
        offset : int
            Pagination offset (0 = newest emails).

        Returns
        -------
        List[Dict[str, Any]]
            List of email metadata dictionaries. Each dict contains
            keys: mail_id, mail_from, mail_subject, mail_timestamp, etc.
            Returns empty list if inbox is empty or API returns nothing.
        """
        try:
            response = self._get(
                action=self._ACTION_GET_EMAIL_LIST,
                params={
                    "sid_token": session_token,
                    "offset": str(offset),
                },
            )
            emails = response.get("list", [])
            if emails:
                logger.debug(f"Inbox has {len(emails)} message(s)")
            return emails if isinstance(emails, list) else []

        except GuerrillaMailError as exc:
            logger.warning(f"Inbox check failed: {exc}")
            return []

    def get_email_body(
        self,
        session_token: str,
        email_id: str,
    ) -> Optional[str]:
        """
        Fetch the full HTML body of a specific email.

        Parameters
        ----------
        session_token : str
            The session token returned by get_email_address().
        email_id : str
            The mail_id of the email to fetch.

        Returns
        -------
        Optional[str]
            The HTML body of the email, or None on failure.
        """
        logger.debug(f"Fetching email body for mail_id={email_id!r}")

        try:
            response = self._get(
                action=self._ACTION_FETCH_EMAIL,
                params={
                    "sid_token": session_token,
                    "email_id": email_id,
                },
            )
            body = response.get("mail_body", "")
            logger.debug(f"Email body fetched: {len(body)} characters")
            return body or None

        except GuerrillaMailError as exc:
            logger.error(f"Failed to fetch email body: {exc}")
            return None

    def wait_for_email_from(
        self,
        session_token: str,
        sender_keyword: str = "chess.com",
        poll_interval: Optional[float] = None,
        max_attempts: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> Optional[Tuple[str, str]]:
        """
        Poll the inbox until an email from a specific sender arrives.

        Parameters
        ----------
        session_token : str
            Guerrilla Mail session token.
        sender_keyword : str
            Case-insensitive substring to match against sender address.
        poll_interval : Optional[float]
            Seconds between polls. Defaults to config.email_poll_interval.
        max_attempts : Optional[int]
            Max polls before giving up. Defaults to config.email_poll_max_attempts.
        progress_callback : Optional[callable]
            Called with (attempt, max_attempts) on each poll attempt.

        Returns
        -------
        Optional[Tuple[str, str]]
            2-tuple of (email_id, email_body) if found, else None.
        """
        interval = poll_interval or config.email_poll_interval
        attempts = max_attempts or config.email_poll_max_attempts
        keyword = sender_keyword.lower()

        logger.info(
            f"Polling inbox for email from {sender_keyword!r} — "
            f"max {attempts} attempts every {interval}s"
        )

        # Track already-seen email IDs to avoid reprocessing
        seen_ids: set = set()

        for attempt in range(1, attempts + 1):
            logger.debug(f"Inbox poll attempt {attempt}/{attempts}...")

            if progress_callback:
                try:
                    progress_callback(attempt, attempts)
                except Exception:
                    pass

            emails = self.check_inbox(session_token)

            for email_meta in emails:
                mail_id = str(email_meta.get("mail_id", ""))
                mail_from = str(email_meta.get("mail_from", "")).lower()

                # Skip already processed emails
                if mail_id in seen_ids:
                    continue
                seen_ids.add(mail_id)

                if keyword in mail_from:
                    logger.success(
                        f"Found email from {email_meta.get('mail_from')!r} "
                        f"(subject: {email_meta.get('mail_subject')!r})"
                    )
                    body = self.get_email_body(session_token, mail_id)
                    return mail_id, body

            # Wait before next poll
            time.sleep(interval)

        logger.warning(
            f"No email from {sender_keyword!r} received after "
            f"{attempts} attempts ({attempts * interval:.0f}s)"
        )
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        action: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request to the Guerrilla Mail API.

        Parameters
        ----------
        action : str
            The API action parameter value.
        params : Optional[Dict[str, str]]
            Additional query parameters.

        Returns
        -------
        Dict[str, Any]
            Parsed JSON response as a dictionary.

        Raises
        ------
        GuerrillaMailError
            On HTTP error, timeout, or non-JSON response.
        """
        all_params = {"f": action}
        if params:
            all_params.update(params)

        try:
            resp = self._session.get(
                self._api_url,
                params=all_params,
                timeout=self._REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            raise GuerrillaMailError(f"Request timed out for action={action!r}")
        except requests.exceptions.HTTPError as exc:
            raise GuerrillaMailError(
                f"HTTP error {exc.response.status_code} for action={action!r}: {exc}"
            )
        except requests.exceptions.RequestException as exc:
            raise GuerrillaMailError(f"Request failed for action={action!r}: {exc}")
        except ValueError as exc:
            raise GuerrillaMailError(
                f"Failed to parse JSON response for action={action!r}: {exc}"
            )

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()
        logger.debug("GuerrillaMailClient HTTP session closed")

    def __enter__(self) -> "GuerrillaMailClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
