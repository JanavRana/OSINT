"""
connectors/reverse_dns/connector.py

Reverse DNS connector implementation using the dnspython library.

This connector:
    1. Subclasses BaseConnector
    2. Registers itself automatically via the @registry.register decorator
    3. Accepts IP identifiers (both IPv4 and IPv6)
    4. Performs reverse DNS lookups (PTR records)
    5. Returns RAW responses without normalization
    6. Does NOT store data, access database, or call FastAPI
"""

from __future__ import annotations

from typing import Any, ClassVar, FrozenSet

import dns.resolver
import dns.reversename

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType


@registry.register
class ReverseDnsConnector(BaseConnector):
    """
    Reverse DNS lookup connector for IP address identifiers.

    Uses the dnspython library to perform reverse DNS lookups (PTR records)
    to resolve IP addresses to domain names. Returns the raw reverse DNS
    data for downstream normalization (M3).
    """

    name: ClassVar[str] = "reverse_dns"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.IP}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> dict[str, Any]:
        """
        Perform reverse DNS lookup for the given IP address identifier.

        Args:
            identifier: An IP identifier (e.g., value="8.8.8.8" or "2001:4860:4860::8888")

        Returns:
            A JSON-serializable dictionary containing the reverse DNS results
            with PTR records mapping the IP to domain name(s).

        Raises:
            dns.exception.DNSException: If reverse DNS query fails
            Exception: Any other error during lookup
        """
        ip_address = identifier.value
        result: dict[str, Any] = {
            "ip_address": ip_address,
            "hostnames": [],
        }

        try:
            # Convert IP address to reverse DNS query name (e.g., "8.8.8.8" -> "8.8.8.8.in-addr.arpa")
            rev_name = dns.reversename.from_address(ip_address)

            # Create resolver with timeout
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout_seconds
            resolver.lifetime = self.timeout_seconds

            # Query PTR records
            answers = resolver.resolve(rev_name, "PTR")

            # Extract hostnames from PTR records
            hostnames = []
            for rdata in answers:
                hostname = str(rdata.target).rstrip(".")
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

            result["hostnames"] = hostnames

        except dns.resolver.NXDOMAIN:
            # No PTR record exists for this IP
            result["error"] = f"No reverse DNS record found for {ip_address} (NXDOMAIN)"
        except dns.resolver.NoAnswer:
            # Query succeeded but no PTR records returned
            result["error"] = f"No PTR records found for {ip_address}"
        except dns.exception.Timeout:
            # Query timed out
            result["error"] = f"Reverse DNS query timed out for {ip_address}"
        except ValueError as e:
            # Invalid IP address format
            result["error"] = f"Invalid IP address format: {e}"
        except Exception as e:
            # Any other error
            result["error"] = f"Reverse DNS lookup failed: {e}"

        return result
