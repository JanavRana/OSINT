"""
connectors/email/validator.py

Email address validation for the Email OSINT connector.

Validates email format using a simplified RFC-5322 regex pattern,
normalizes to lowercase, and extracts local_part and domain components.

Uses only stdlib — zero external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class EmailValidationError(ValueError):
    """Raised when an email address string is invalid or malformed."""


@dataclass(frozen=True)
class EmailValidationResult:
    """Result of a successful email address validation."""

    email: str           # The normalized email (lowercase, trimmed)
    local_part: str      # The part before @
    domain: str          # The part after @


# Simplified RFC-5322 email validation pattern
# This is intentionally simplified for OSINT purposes - focuses on common formats
# Does NOT perform SMTP verification or handle all edge cases
_EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)


def validate_email_address(raw: str) -> EmailValidationResult:
    """
    Parse and validate a raw email address string.

    Accepts:
        - Standard email format (e.g., "user@example.com")
        - Normalizes to lowercase
        - Trims whitespace

    Rejects (raises EmailValidationError):
        - Empty strings
        - Missing @ symbol
        - Invalid characters
        - Malformed domain
        - Multiple @ symbols (not in quoted strings)

    Does NOT perform:
        - SMTP mailbox verification
        - DNS MX record validation (done by connector)
        - Disposable email detection (done by connector)

    Args:
        raw: Raw email address string

    Raises:
        EmailValidationError: if the input cannot be parsed as a valid email

    Returns:
        EmailValidationResult with normalized email and extracted components
    """
    if not isinstance(raw, str) or not raw.strip():
        raise EmailValidationError("Email address must be a non-empty string.")

    # Normalize: trim and lowercase
    normalized = raw.strip().lower()

    # Basic validation with regex
    if not _EMAIL_PATTERN.match(normalized):
        raise EmailValidationError(
            f"'{raw}' is not a valid email address format. "
            "Expected format: user@example.com"
        )

    # Split into local_part and domain
    # We already validated with regex, so we know there's exactly one @
    try:
        local_part, domain = normalized.rsplit('@', 1)
    except ValueError as exc:
        raise EmailValidationError(
            f"'{raw}' must contain exactly one @ symbol."
        ) from exc

    if not local_part:
        raise EmailValidationError(
            f"'{raw}' has an empty local part (before @)."
        )

    if not domain:
        raise EmailValidationError(
            f"'{raw}' has an empty domain (after @)."
        )

    # Additional validation: domain must have at least one dot
    if '.' not in domain:
        raise EmailValidationError(
            f"'{raw}' has an invalid domain '{domain}' (must contain at least one dot)."
        )

    return EmailValidationResult(
        email=normalized,
        local_part=local_part,
        domain=domain,
    )
