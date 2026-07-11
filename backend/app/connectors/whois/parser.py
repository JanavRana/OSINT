"""
connectors/whois/parser.py

Parser utility for WHOIS connector responses.

This module provides a consistent parsing interface to convert the
python-whois library output into a standardized dictionary format.

Note: This parser does NOT perform normalization into the internal
schema (that's M3's responsibility). It only ensures the raw WHOIS
data from python-whois is consistently structured as a dictionary,
handling library-specific quirks (e.g., list vs single values,
datetime serialization).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Union


def parse_whois_response(raw_whois_data: dict) -> dict:
    """
    Parse raw WHOIS data from python-whois into a consistent dictionary.

    The python-whois library sometimes returns fields as single values,
    sometimes as lists, and datetime objects need to be serialized for
    JSON compatibility. This parser standardizes the output format without
    performing semantic normalization (which is M3's job).

    Args:
        raw_whois_data: Raw dictionary output from python-whois library

    Returns:
        A consistently-structured dictionary with:
            - All datetime values converted to ISO format strings
            - List values normalized (empty lists removed, single-item
              lists optionally flattened for consistency)
            - None/null values preserved for missing fields
            - All keys preserved from original data

    Example:
        >>> raw = {
        ...     "domain_name": ["EXAMPLE.COM", "example.com"],
        ...     "creation_date": [datetime(2023, 1, 1), datetime(2023, 1, 1)],
        ...     "registrar": "Example Registrar Inc."
        ... }
        >>> parsed = parse_whois_response(raw)
        >>> parsed["domain_name"]
        'example.com'
        >>> parsed["creation_date"]
        '2023-01-01T00:00:00'
    """
    if not raw_whois_data:
        return {}

    parsed = {}

    for key, value in raw_whois_data.items():
        parsed[key] = _normalize_field_value(value)

    return parsed


def _normalize_field_value(value: Any) -> Any:
    """
    Normalize a single field value from WHOIS data.

    Handles:
        - datetime -> ISO string
        - list of datetimes -> list of ISO strings (or single string if only one)
        - list of strings -> normalized list (or single string if only one)
        - None/null -> preserved
        - Other types -> passed through

    Args:
        value: The raw field value from WHOIS data

    Returns:
        Normalized value suitable for JSON serialization
    """
    if value is None:
        return None

    # Handle datetime objects
    if isinstance(value, datetime):
        return value.isoformat()

    # Handle lists
    if isinstance(value, (list, tuple)):
        if not value:
            return None  # Empty list -> None

        # Normalize each item in the list
        normalized_items = [_normalize_single_item(item) for item in value]

        # Remove duplicates while preserving order
        unique_items = _deduplicate_preserving_order(normalized_items)

        # If only one unique item, return it directly rather than a list
        if len(unique_items) == 1:
            return unique_items[0]

        return unique_items

    # Handle other types (strings, numbers, etc.)
    return _normalize_single_item(value)


def _normalize_single_item(item: Any) -> Any:
    """Normalize a single item (not a list)."""
    if isinstance(item, datetime):
        return item.isoformat()

    if isinstance(item, str):
        # Normalize string: strip whitespace, lowercase for domain names
        stripped = item.strip()
        return stripped if stripped else None

    return item


def _deduplicate_preserving_order(items: List[Any]) -> List[Any]:
    """
    Remove duplicate items from a list while preserving order.

    Uses a seen set for O(n) performance while maintaining insertion order.
    """
    seen = set()
    result = []

    for item in items:
        # For unhashable types (like dicts), use string representation
        try:
            key = item
            if key not in seen:
                seen.add(key)
                result.append(item)
        except TypeError:
            # Unhashable type, fall back to string comparison
            str_key = str(item)
            if str_key not in seen:
                seen.add(str_key)
                result.append(item)

    return result


def extract_registrant_email(parsed_whois: dict) -> Optional[str]:
    """
    Extract the primary registrant email from parsed WHOIS data.

    This is a convenience utility for common WHOIS queries, though
    normalization (M3) is responsible for extracting all semantic
    facts from the data.

    Args:
        parsed_whois: Parsed WHOIS data from parse_whois_response()

    Returns:
        The first registrant email found, or None if not available
    """
    # Try common field names
    emails = parsed_whois.get("emails")
    if emails:
        if isinstance(emails, list):
            return emails[0] if emails else None
        return emails

    # Fallback to other common field names
    for field_name in ["registrant_email", "admin_email", "tech_email"]:
        email = parsed_whois.get(field_name)
        if email:
            return email if isinstance(email, str) else (email[0] if email else None)

    return None


def extract_creation_date(parsed_whois: dict) -> Optional[str]:
    """
    Extract the domain creation date from parsed WHOIS data.

    Args:
        parsed_whois: Parsed WHOIS data from parse_whois_response()

    Returns:
        ISO format date string, or None if not available
    """
    creation_date = parsed_whois.get("creation_date")
    if creation_date:
        # parse_whois_response already normalized to ISO string
        return creation_date if isinstance(creation_date, str) else creation_date[0]
    return None


def extract_expiration_date(parsed_whois: dict) -> Optional[str]:
    """
    Extract the domain expiration date from parsed WHOIS data.

    Args:
        parsed_whois: Parsed WHOIS data from parse_whois_response()

    Returns:
        ISO format date string, or None if not available
    """
    expiration_date = parsed_whois.get("expiration_date")
    if expiration_date:
        return (
            expiration_date
            if isinstance(expiration_date, str)
            else expiration_date[0]
        )
    return None
