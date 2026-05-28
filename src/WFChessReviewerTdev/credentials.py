"""
credentials.py — Random Credential Generator
=============================================
Generates cryptographically random usernames and passwords
suitable for Chess.com account registration.

Design goals:
  - Usernames look "human" (adjective + noun + random suffix pattern)
  - Passwords meet Chess.com complexity requirements (16+ chars,
    uppercase, lowercase, digit, special character)
  - Uses Python's secrets module for cryptographic randomness
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Word banks for human-looking username generation
# ---------------------------------------------------------------------------
_ADJECTIVES = [
    "swift",
    "bold",
    "clever",
    "dark",
    "silent",
    "royal",
    "ancient",
    "fierce",
    "noble",
    "brave",
    "sharp",
    "quick",
    "mighty",
    "calm",
    "steel",
    "iron",
    "golden",
    "silver",
    "cosmic",
    "storm",
    "shadow",
    "frost",
    "flame",
    "night",
    "dawn",
    "wild",
    "free",
    "lone",
    "epic",
    "grand",
    "deep",
    "vast",
    "keen",
    "wise",
    "true",
    "fast",
    "hard",
]

_NOUNS = [
    "knight",
    "bishop",
    "rook",
    "pawn",
    "king",
    "queen",
    "castle",
    "gambit",
    "player",
    "master",
    "bishop",
    "tactician",
    "strategist",
    "champion",
    "rival",
    "hunter",
    "seeker",
    "warrior",
    "sage",
    "legend",
    "ace",
    "expert",
    "veteran",
    "prodigy",
    "champion",
    "tactician",
]

_SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}|;:,.<>?"


@dataclass
class Credentials:
    """
    Container for generated registration credentials.

    Attributes
    ----------
    email : str
        Temporary email address from Guerrilla Mail.
    username : str
        Randomly generated Chess.com-compatible username.
    password : str
        Randomly generated strong password.
    session_token : Optional[str]
        Guerrilla Mail session token for inbox polling.
    """

    email: str
    username: str
    password: str
    session_token: Optional[str] = None

    def display_string(self) -> str:
        """
        Return a human-readable multi-line credential summary.

        Returns
        -------
        str
            Formatted credentials string for display/clipboard.
        """
        return (
            f"Email:    {self.email}\n"
            f"Username: {self.username}\n"
            f"Password: {self.password}"
        )

    def to_dict(self) -> dict:
        """
        Serialize credentials to a plain dictionary (for JSON export).

        Returns
        -------
        dict
            Dictionary with email, username, password keys.
        """
        return {
            "email": self.email,
            "username": self.username,
            "password": self.password,
        }


class CredentialGenerator:
    """
    Generates random, human-looking usernames and strong passwords.

    All methods are static — no instance state is required.

    Examples
    --------
    >>> gen = CredentialGenerator()
    >>> username = gen.generate_username()
    >>> password = gen.generate_password()
    >>> creds = gen.generate(email="test@example.com")
    """

    @staticmethod
    def generate_username(max_length: int = 20) -> str:
        """
        Generate a random Chess.com-compatible username.

        Format: {adjective}_{noun}_{suffix}
        Where suffix is 4-6 random alphanumeric characters.
        Total length is capped at max_length characters.

        Parameters
        ----------
        max_length : int
            Maximum allowed username length (Chess.com limit is ~20).

        Returns
        -------
        str
            A random username string.
        """
        adjective = secrets.choice(_ADJECTIVES)
        noun = secrets.choice(_NOUNS)

        # Generate suffix: 4-6 alphanumeric characters
        suffix_length = secrets.randbelow(3) + 4  # 4, 5, or 6
        alphabet = string.ascii_lowercase + string.digits
        suffix = "".join(secrets.choice(alphabet) for _ in range(suffix_length))

        username = f"{adjective}_{noun}_{suffix}"

        # Truncate if necessary while keeping suffix intact
        if len(username) > max_length:
            available = max_length - len(suffix) - 1  # -1 for underscore
            username = f"{adjective[:available]}_{suffix}"

        logger.debug(f"Generated username: {username!r}")
        return username

    @staticmethod
    def generate_password(length: int = 18) -> str:
        """
        Generate a cryptographically strong password meeting Chess.com rules.

        Password requirements:
          - At least 16 characters (we default to 18 for safety)
          - At least one uppercase letter
          - At least one lowercase letter
          - At least one digit
          - At least one special character

        Parameters
        ----------
        length : int
            Total password length (minimum 16, defaults to 18).

        Returns
        -------
        str
            A strong random password string.

        Raises
        ------
        ValueError
            If requested length is less than 8 (too short to be safe).
        """
        if length < 8:
            raise ValueError(f"Password length {length} is too short. Minimum is 8.")
        # Use max(length, 16) to enforce minimum complexity length
        actual_length = max(length, 16)

        # Guarantee at least one character from each required category
        guaranteed = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice(_SPECIAL_CHARS),
        ]

        # Fill remaining characters from the full pool
        full_pool = (
            string.ascii_uppercase
            + string.ascii_lowercase
            + string.digits
            + _SPECIAL_CHARS
        )
        remaining_length = actual_length - len(guaranteed)
        remaining = [secrets.choice(full_pool) for _ in range(remaining_length)]

        # Combine and shuffle to avoid predictable positions
        password_chars = guaranteed + remaining
        # Use Fisher-Yates shuffle via secrets for cryptographic randomness
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = (
                password_chars[j],
                password_chars[i],
            )

        password = "".join(password_chars)
        logger.debug(
            f"Generated password of length {len(password)} "
            f"(uppercase: ✓, lowercase: ✓, digit: ✓, special: ✓)"
        )
        return password

    @classmethod
    def generate(
        cls,
        email: str,
        session_token: Optional[str] = None,
    ) -> Credentials:
        """
        Generate a complete Credentials object.

        Parameters
        ----------
        email : str
            The temporary email address to embed in credentials.
        session_token : Optional[str]
            Guerrilla Mail session token for later inbox polling.

        Returns
        -------
        Credentials
            Fully populated credentials object ready for registration.
        """
        username = cls.generate_username()
        password = cls.generate_password()

        creds = Credentials(
            email=email,
            username=username,
            password=password,
            session_token=session_token,
        )
        logger.info(
            f"Credentials generated — " f"email={email!r}, username={creds.username!r}"
        )
        return creds
