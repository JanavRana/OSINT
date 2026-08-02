"""
connectors/dns/connector.py

DNS connector implementation using the dnspython library.

This connector:
    1. Subclasses BaseConnector
    2. Registers itself automatically via the @registry.register decorator
    3. Accepts DOMAIN and IP identifiers
    4. Performs DNS lookups (A, AAAA, MX, NS, TXT, CNAME, SOA records)
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
class DnsConnector(BaseConnector):
    """
    DNS lookup connector for domain identifiers.

    Uses the dnspython library to perform DNS queries for various record
    types (A, AAAA, MX, NS, TXT, CNAME, SOA). Returns the raw DNS data
    for downstream normalization (M3).
    """

    name: ClassVar[str] = "dns"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.DOMAIN}
    )
    timeout_seconds: ClassVar[float] = 10.0

    # Record types to query
    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

    async def fetch(self, identifier: Identifier) -> dict[str, Any]:
        """
        Perform DNS lookup for the given domain identifier.

        Args:
            identifier: A domain identifier (e.g., value="example.com")

        Returns:
            A JSON-serializable dictionary containing DNS records organized
            by record type. Each record type maps to a list of record data.

        Raises:
            dns.exception.DNSException: If DNS query fails
            Exception: Any other error during lookup
        """
        domain = identifier.value
        result: dict[str, Any] = {
            "domain": domain,
            "records": {},
        }

        resolver = dns.resolver.Resolver()
        resolver.timeout = self.timeout_seconds
        resolver.lifetime = self.timeout_seconds

        for record_type in self.RECORD_TYPES:
            try:
                answers = resolver.resolve(domain, record_type)
                records = []

                for rdata in answers:
                    if record_type in ["A", "AAAA"]:
                        records.append({"address": str(rdata)})
                    elif record_type == "MX":
                        records.append({
                            "preference": rdata.preference,
                            "exchange": str(rdata.exchange),
                        })
                    elif record_type == "NS":
                        records.append({"nameserver": str(rdata)})
                    elif record_type == "TXT":
                        # TXT records are returned as byte strings, join them
                        txt_value = b"".join(rdata.strings).decode("utf-8", errors="replace")
                        records.append({"text": txt_value})
                    elif record_type == "CNAME":
                        records.append({"cname": str(rdata.target)})
                    elif record_type == "SOA":
                        records.append({
                            "mname": str(rdata.mname),
                            "rname": str(rdata.rname),
                            "serial": rdata.serial,
                            "refresh": rdata.refresh,
                            "retry": rdata.retry,
                            "expire": rdata.expire,
                            "minimum": rdata.minimum,
                        })
                    else:
                        records.append({"data": str(rdata)})

                if records:
                    result["records"][record_type] = records

            except dns.resolver.NoAnswer:
                # No records of this type exist, skip
                continue
            except dns.resolver.NXDOMAIN:
                # Domain doesn't exist
                result["error"] = f"Domain {domain} does not exist (NXDOMAIN)"
                break
            except dns.exception.Timeout:
                # Timeout for this record type, continue with others
                continue
            except Exception:
                # Any other error for this record type, continue with others
                continue

        return result
