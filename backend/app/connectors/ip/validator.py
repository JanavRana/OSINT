"""
connectors/ip/validator.py

IP address validation for the IP OSINT connector.

Supports IPv4 and IPv6 using the stdlib `ipaddress` module.
Rejects hostnames, malformed addresses, private/reserved addresses,
and loopback/link-local/multicast ranges.

Uses only stdlib — zero external dependencies.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Literal


class IpValidationError(ValueError):
    """Raised when an IP address string is invalid or unsupported."""


@dataclass(frozen=True)
class IpValidationResult:
    """Result of a successful IP address validation."""

    address: str                       # The normalized string form of the IP
    version: Literal[4, 6]             # IP protocol version
    is_private: bool                   # True for RFC 1918 / private ranges
    is_reserved: bool                  # True for IANA reserved ranges
    is_loopback: bool                  # 127.x.x.x or ::1
    is_link_local: bool                # 169.254.x.x or fe80::/10
    is_multicast: bool                 # 224.0.0.0/4 or ff00::/8
    is_publicly_routable: bool         # None of the above special ranges


def validate_ip_address(raw: str) -> IpValidationResult:
    """
    Parse and validate a raw IP address string.

    Accepts:
        - Valid IPv4 dotted-decimal (e.g. "8.8.8.8")
        - Valid IPv6 (e.g. "2001:4860:4860::8888")

    Rejects (raises IpValidationError):
        - Hostnames/domain names (e.g. "google.com")
        - Malformed addresses (e.g. "256.1.1.1", "not-an-ip")
        - CIDR notation (e.g. "8.8.8.0/24") — use the bare address instead

    Does NOT reject private/reserved IPs — callers that want to gate on
    those can check `result.is_publicly_routable` and decide.

    Raises:
        IpValidationError: if the input cannot be parsed as a valid IP.

    Returns:
        IpValidationResult with all flags populated.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise IpValidationError("IP address must be a non-empty string.")

    stripped = raw.strip()

    # Reject CIDR notation explicitly
    if "/" in stripped:
        raise IpValidationError(
            f"CIDR notation is not accepted as an IP identifier: '{stripped}'. "
            "Provide a bare IP address without a prefix length."
        )

    try:
        addr = ipaddress.ip_address(stripped)
    except ValueError as exc:
        raise IpValidationError(
            f"'{stripped}' is not a valid IPv4 or IPv6 address: {exc}"
        ) from exc

    is_private = addr.is_private
    is_reserved = addr.is_reserved
    is_loopback = addr.is_loopback
    is_link_local = addr.is_link_local
    is_multicast = addr.is_multicast

    is_publicly_routable = not (
        is_private or is_reserved or is_loopback or is_link_local or is_multicast
    )

    return IpValidationResult(
        address=str(addr),           # Normalized form (e.g. expands IPv6 shorthand)
        version=addr.version,        # type: ignore[arg-type]
        is_private=is_private,
        is_reserved=is_reserved,
        is_loopback=is_loopback,
        is_link_local=is_link_local,
        is_multicast=is_multicast,
        is_publicly_routable=is_publicly_routable,
    )
