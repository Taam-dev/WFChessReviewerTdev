"""
Tests for credentials.py — CredentialGenerator and Credentials.

All tests are pure unit tests requiring no network or browser.
"""

from __future__ import annotations

import re
import string

import pytest

from WFChessReviewerTdev.credentials import (
    CredentialGenerator,
    Credentials,
)


class TestCredentials:
    """Tests for the Credentials dataclass."""

    def test_credentials_creation(self) -> None:
        """Credentials can be instantiated with all fields."""
        creds = Credentials(
            email="test@grr.la",
            username="swift_knight_a3x9",
            password="SecurePass123!@",
            session_token="abc123token",
        )
        assert creds.email == "test@grr.la"
        assert creds.username == "swift_knight_a3x9"
        assert creds.password == "SecurePass123!@"
        assert creds.session_token == "abc123token"

    def test_credentials_optional_session_token(self) -> None:
        """session_token defaults to None when not provided."""
        creds = Credentials(
            email="x@y.com",
            username="user123",
            password="Pass!234",
        )
        assert creds.session_token is None

    def test_display_string_format(self) -> None:
        """display_string() returns all three credential fields."""
        creds = Credentials(
            email="test@grr.la",
            username="my_user",
            password="MyP@ssw0rd!!",
        )
        display = creds.display_string()
        assert "test@grr.la" in display
        assert "my_user" in display
        assert "MyP@ssw0rd!!" in display
        # Should be multi-line
        assert display.count("\n") >= 2

    def test_to_dict_keys(self) -> None:
        """to_dict() returns a dict with the three expected keys."""
        creds = Credentials(
            email="a@b.com",
            username="u1",
            password="p1",
        )
        d = creds.to_dict()
        assert set(d.keys()) == {"email", "username", "password"}
        assert d["email"] == "a@b.com"

    def test_to_dict_excludes_session_token(self) -> None:
        """to_dict() should not expose session_token in output."""
        creds = Credentials("a@b.com", "u", "p", session_token="secret")
        assert "session_token" not in creds.to_dict()


class TestCredentialGenerator:
    """Tests for CredentialGenerator static methods."""

    # ── Username tests ────────────────────────────────────────────────

    def test_generate_username_format(self) -> None:
        """Generated username follows adjective_noun_suffix pattern."""
        username = CredentialGenerator.generate_username()
        # Must contain at least one underscore
        assert "_" in username
        parts = username.split("_")
        assert len(parts) >= 2

    def test_generate_username_length_constraint(self) -> None:
        """Generated username respects max_length."""
        for _ in range(20):
            username = CredentialGenerator.generate_username(max_length=20)
            assert len(username) <= 20, f"Username {username!r} exceeds max_length=20"

    def test_generate_username_alphanumeric_underscore(self) -> None:
        """Username contains only letters, digits, and underscores."""
        for _ in range(50):
            username = CredentialGenerator.generate_username()
            assert re.match(
                r"^[a-z0-9_]+$", username
            ), f"Username {username!r} contains invalid characters"

    def test_generate_username_uniqueness(self) -> None:
        """50 generated usernames should have at least 40 unique values."""
        usernames = {CredentialGenerator.generate_username() for _ in range(50)}
        assert (
            len(usernames) >= 40
        ), f"Poor uniqueness: only {len(usernames)} unique usernames from 50"

    # ── Password tests ────────────────────────────────────────────────

    def test_generate_password_minimum_length(self) -> None:
        """Password is at least 16 characters long."""
        for _ in range(20):
            pw = CredentialGenerator.generate_password()
            assert len(pw) >= 16, f"Password too short: {len(pw)}"

    def test_generate_password_custom_length(self) -> None:
        """Custom length is respected (minimum 16)."""
        pw = CredentialGenerator.generate_password(length=20)
        assert len(pw) >= 20

    def test_generate_password_has_uppercase(self) -> None:
        """Password contains at least one uppercase letter."""
        for _ in range(20):
            pw = CredentialGenerator.generate_password()
            assert any(
                c in string.ascii_uppercase for c in pw
            ), f"No uppercase in password: {pw!r}"

    def test_generate_password_has_lowercase(self) -> None:
        """Password contains at least one lowercase letter."""
        for _ in range(20):
            pw = CredentialGenerator.generate_password()
            assert any(
                c in string.ascii_lowercase for c in pw
            ), f"No lowercase in password: {pw!r}"

    def test_generate_password_has_digit(self) -> None:
        """Password contains at least one digit."""
        for _ in range(20):
            pw = CredentialGenerator.generate_password()
            assert any(c in string.digits for c in pw), f"No digit in password: {pw!r}"

    def test_generate_password_has_special_char(self) -> None:
        """Password contains at least one special character."""
        special = set("!@#$%^&*()-_=+[]{}|;:,.<>?")
        for _ in range(20):
            pw = CredentialGenerator.generate_password()
            assert any(c in special for c in pw), f"No special char in password: {pw!r}"

    def test_generate_password_rejects_too_short(self) -> None:
        """ValueError is raised for length < 8."""
        with pytest.raises(ValueError, match="too short"):
            CredentialGenerator.generate_password(length=4)

    def test_generate_password_uniqueness(self) -> None:
        """50 passwords should all be unique."""
        passwords = {CredentialGenerator.generate_password() for _ in range(50)}
        assert len(passwords) == 50, "Duplicate passwords generated!"

    # ── Full generate() tests ─────────────────────────────────────────

    def test_generate_returns_credentials_object(self) -> None:
        """generate() returns a proper Credentials instance."""
        creds = CredentialGenerator.generate(email="test@example.com")
        assert isinstance(creds, Credentials)

    def test_generate_embeds_email(self) -> None:
        """generate() uses the provided email address."""
        email = "myfakemail@grr.la"
        creds = CredentialGenerator.generate(email=email)
        assert creds.email == email

    def test_generate_with_session_token(self) -> None:
        """generate() stores the provided session_token."""
        token = "mysessiontoken123"
        creds = CredentialGenerator.generate(
            email="x@y.com",
            session_token=token,
        )
        assert creds.session_token == token

    def test_generate_creates_valid_username_and_password(self) -> None:
        """generate() produces non-empty username and password."""
        creds = CredentialGenerator.generate(email="test@test.com")
        assert creds.username
        assert creds.password
        assert len(creds.password) >= 16
