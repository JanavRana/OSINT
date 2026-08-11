"""
connectors/mac/validator.py

MAC address validation and normalization utility.

Supports MAC addresses in:
- Colon notation: 00:1A:2B:3C:4D:5E (or lowercase 00:1a:2b:3c:4d:5e)
- Hyphen notation: 00-1A-2B-3C-4D-5E
- Cisco dot notation: 001a.2b3c.4d5e
- Bare hex string: 001A2B3C4D5E

Rejects malformed strings, non-hex characters, and incorrect lengths.
Uses stdlib only — zero external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class MacValidationError(ValueError):
    """Raised when a string cannot be parsed as a valid MAC address."""


@dataclass(frozen=True)
class MacValidationResult:
    """Result of a successful MAC address validation."""

    raw_input: str
    normalized: str        # Formatted as standard upper colon "00:1A:2B:3C:4D:5E"
    oui_prefix: str        # First 3 octets "00:1A:2B"
    is_multicast: bool     # True if lowest bit of first octet is 1
    is_locally_administered: bool  # True if second lowest bit of first octet is 1


# Match colon, hyphen, Cisco dot, or bare hex formats
_MAC_REGEX = re.compile(
    r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|"
    r"^(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$|"
    r"^[0-9A-Fa-f]{12}$"
)


def validate_mac_address(raw: str) -> MacValidationResult:
    """
    Validate and normalize a MAC address string.

    Args:
        raw: MAC address string in colon, hyphen, dot, or bare hex format.

    Returns:
        MacValidationResult with normalized forms and OUI prefix.

    Raises:
        MacValidationError: If the input is not a valid 48-bit MAC address.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise MacValidationError("MAC address must be a non-empty string.")

    stripped = raw.strip()
    if not _MAC_REGEX.match(stripped):
        raise MacValidationError(
            f"'{stripped}' is not a valid 48-bit MAC address. "
            "Expected format e.g. 00:1A:2B:3C:4D:5E, 00-1A-2B-3C-4D-5E, or 001a.2b3c.4d5e."
        )

    # Clean to 12 uppercase hex digits
    hex_digits = re.sub(r"[^0-9A-Fa-f]", "", stripped).upper()
    if len(hex_digits) != 12:
        raise MacValidationError(f"MAC address must contain 12 hex digits, got {len(hex_digits)}.")

    # Pair into 6 octets
    octets = [hex_digits[i : i + 2] for i in range(0, 12, 2)]
    normalized = ":".join(octets)
    oui_prefix = ":".join(octets[:3])

    first_byte = int(octets[0], 16)
    is_multicast = bool(first_byte & 0x01)
    is_locally_administered = bool(first_byte & 0x02)

    return MacValidationResult(
        raw_input=raw,
        normalized=normalized,
        oui_prefix=oui_prefix,
        is_multicast=is_multicast,
        is_locally_administered=is_locally_administered,
    )
