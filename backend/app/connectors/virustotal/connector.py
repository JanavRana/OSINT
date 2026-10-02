"""
connectors/virustotal/connector.py

VirusTotal v3 REST API Threat Intelligence Connector.

Queries VirusTotal v3 endpoints for DOMAIN and IP target identifiers to extract:
- Multi-engine security analysis stats (malicious, suspicious, harmless, undetected)
- Community reputation score
- Threat categories and tags (phishing, malware, vpn, tor-exit, etc.)
- Autonomous System / ISP ownership & location (for IPs)
- Passive DNS history records (for Domains)
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar, Dict, FrozenSet

import httpx

from ...core.config import get_settings
from ..base import BaseConnector
from ..ip.validator import IpValidationError, validate_ip_address
from ..registry import registry
from ..types import Identifier, IdentifierType

logger = logging.getLogger("osint-aggregator")


@registry.register
class VirusTotalConnector(BaseConnector):
    """
    VirusTotal v3 OSINT Threat Intelligence Connector.

    Supports `IdentifierType.DOMAIN` and `IdentifierType.IP`.
    Queries VirusTotal v3 REST API using x-apikey authentication.
    """

    name: ClassVar[str] = "virustotal"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.DOMAIN, IdentifierType.IP}
    )
    timeout_seconds: ClassVar[float] = 12.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Query VirusTotal v3 API for domain or IP intelligence.
        """
        raw_value = identifier.value.strip()
        settings = get_settings()

        result: Dict[str, Any] = {
            "target": raw_value,
            "target_type": identifier.type.value,
            "vt_matched": False,
            "reputation": None,
            "last_analysis_stats": {},
            "categories": {},
            "tags": [],
            "whois": None,
            "as_owner": None,
            "asn": None,
            "country": None,
            "last_dns_records": [],
            "error": None,
            "error_code": None,
        }

        # 1. Check for VirusTotal API key
        api_key = (
            os.environ.get("VIRUSTOTAL_API_KEY")
            or getattr(settings, "virustotal_api_key", None)
        )
        if not api_key:
            logger.info("VIRUSTOTAL_API_KEY not configured; skipping VirusTotal query.")
            result["error"] = "VIRUSTOTAL_API_KEY not set"
            result["error_code"] = "api_key_missing"
            return result

        api_key = api_key.strip()

        # 2. Build URL based on identifier type
        if identifier.type == IdentifierType.IP:
            try:
                val = validate_ip_address(raw_value)
                if not val.is_publicly_routable:
                    logger.info("IP %s is non-routable; skipping VirusTotal query.", raw_value)
                    result["error"] = "Non-routable IP address"
                    result["error_code"] = "private_ip"
                    return result
                raw_value = val.address
            except IpValidationError as exc:
                result["error"] = str(exc)
                result["error_code"] = "validation_error"
                return result

            url = f"https://www.virustotal.com/api/v3/ip_addresses/{raw_value}"
        elif identifier.type == IdentifierType.DOMAIN:
            domain_val = raw_value.lower().rstrip(".")
            url = f"https://www.virustotal.com/api/v3/domains/{domain_val}"
        else:
            result["error"] = f"Unsupported identifier type: {identifier.type}"
            result["error_code"] = "unsupported_type"
            return result

        headers = {
            "x-apikey": api_key,
            "Accept": "application/json",
            "User-Agent": "OSINT-Aggregator/1.0",
        }

        # 3. Perform HTTP request
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)

                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data") or {}
                    attributes = data.get("attributes") or {}

                    result["vt_matched"] = True
                    result["reputation"] = attributes.get("reputation")
                    result["last_analysis_stats"] = attributes.get("last_analysis_stats") or {}
                    result["categories"] = attributes.get("categories") or {}
                    result["tags"] = attributes.get("tags") or []
                    result["whois"] = attributes.get("whois")
                    result["as_owner"] = attributes.get("as_owner")
                    result["asn"] = attributes.get("asn")
                    result["country"] = attributes.get("country")

                    # Extract DNS history if domain
                    dns_records = attributes.get("last_dns_records") or []
                    if isinstance(dns_records, list):
                        extracted_dns = []
                        for rec in dns_records[:10]:  # Limit to 10 key records
                            if isinstance(rec, dict):
                                extracted_dns.append({
                                    "type": rec.get("type"),
                                    "value": rec.get("value"),
                                    "ttl": rec.get("ttl"),
                                })
                        result["last_dns_records"] = extracted_dns

                elif resp.status_code == 404:
                    logger.info("Target %s not found in VirusTotal database.", raw_value)
                    result["error"] = "Target not found in VirusTotal database"
                    result["error_code"] = 404
                elif resp.status_code in (401, 403):
                    logger.warning("VirusTotal API unauthorized (%s) - check API key", resp.status_code)
                    result["error"] = "Invalid or unverified VirusTotal API key"
                    result["error_code"] = resp.status_code
                elif resp.status_code == 429:
                    logger.warning("VirusTotal API rate limit (429) reached.")
                    result["error"] = "Rate limit exceeded (4 req/min free limit)"
                    result["error_code"] = 429
                else:
                    logger.warning("VirusTotal API HTTP %s for %s", resp.status_code, raw_value)
                    result["error"] = f"HTTP {resp.status_code}"
                    result["error_code"] = resp.status_code

        except httpx.TimeoutException:
            logger.warning("VirusTotal API timeout for %s", raw_value)
            result["error"] = "Timeout"
            result["error_code"] = "timeout"
        except Exception as exc:
            logger.warning("VirusTotal API request failed for %s: %s", raw_value, exc)
            result["error"] = str(exc)
            result["error_code"] = "provider_error"

        return result
