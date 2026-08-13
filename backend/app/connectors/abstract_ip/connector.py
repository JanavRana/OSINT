"""
connectors/abstract_ip/connector.py

Abstract IP Geolocation & Anonymity OSINT Connector.

Queries https://ipgeolocation.abstractapi.com/v1/ to extract:
- Security & Anonymity flags: is_vpn, is_tor, is_proxy, is_datacenter, threat_level
- Physical Location: City, Region, Country, Latitude/Longitude
- Infrastructure: ISP, Organization, ASN
- Timezone & GMT Offset
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar, Dict, FrozenSet, Optional

import httpx

from ..base import BaseConnector
from ..ip.validator import IpValidationError, validate_ip_address
from ..registry import registry
from ..types import Identifier, IdentifierType

logger = logging.getLogger("osint-aggregator")


@registry.register
class AbstractIpConnector(BaseConnector):
    """
    Abstract IP Geolocation & Threat Intelligence Connector.

    Supports `IdentifierType.IP`.
    Queries Abstract API to extract anonymity risk flags (VPN, Tor, Proxy, Datacenter)
    and detailed location/ISP metadata.
    """

    name: ClassVar[str] = "abstract_ip"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.IP}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Validate IP address and query Abstract IP Geolocation API.
        """
        raw_value = identifier.value.strip()

        result: Dict[str, Any] = {
            "ip": raw_value,
            "version": None,
            "is_publicly_routable": True,
            "city": None,
            "region": None,
            "postal_code": None,
            "country": None,
            "country_code": None,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "gmt_offset": None,
            "isp": None,
            "organization": None,
            "asn": None,
            "is_vpn": False,
            "is_tor": False,
            "is_proxy": False,
            "is_datacenter": False,
            "threat_level": None,
            "abstract_matched": False,
            "error": None,
            "error_code": None,
        }

        # 1. Validate IP address
        try:
            val = validate_ip_address(raw_value)
            result["ip"] = val.address
            result["version"] = val.version
            result["is_publicly_routable"] = val.is_publicly_routable
        except IpValidationError as exc:
            result["error"] = str(exc)
            result["error_code"] = "validation_error"
            return result

        # 2. Skip non-routable (private/loopback) IPs
        if not val.is_publicly_routable:
            logger.info("IP %s is private/loopback; skipping Abstract API query.", val.address)
            return result

        # 3. Check for API key
        api_key = os.environ.get("ABSTRACT_IP_API_KEY") or os.environ.get("ABSTRACT_API_KEY")
        if not api_key:
            logger.info("ABSTRACT_IP_API_KEY not configured; skipping Abstract IP lookup.")
            result["error"] = "ABSTRACT_IP_API_KEY not set"
            result["error_code"] = "api_key_missing"
            return result

        # 4. Query Abstract IP Intelligence API
        url = "https://ip-intelligence.abstractapi.com/v1/"
        params = {"api_key": api_key.strip(), "ip_address": val.address}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    result["abstract_matched"] = True

                    # 1. Location (nested dictionary in IP Intelligence API v1)
                    loc_data = data.get("location") or {}
                    if isinstance(loc_data, dict):
                        result["city"] = loc_data.get("city")
                        result["region"] = loc_data.get("region")
                        result["postal_code"] = loc_data.get("postal_code")
                        result["country"] = loc_data.get("country")
                        result["country_code"] = loc_data.get("country_code")
                        result["latitude"] = loc_data.get("latitude")
                        result["longitude"] = loc_data.get("longitude")
                    else:
                        # Fallback for top-level keys
                        result["city"] = data.get("city")
                        result["region"] = data.get("region")
                        result["postal_code"] = data.get("postal_code")
                        result["country"] = data.get("country")
                        result["country_code"] = data.get("country_code")
                        result["latitude"] = data.get("latitude")
                        result["longitude"] = data.get("longitude")

                    # 2. Timezone
                    tz_data = data.get("timezone") or {}
                    if isinstance(tz_data, dict):
                        result["timezone"] = tz_data.get("name")
                        result["gmt_offset"] = tz_data.get("utc_offset") or tz_data.get("gmt_offset")

                    # 3. Connection / ASN / Company
                    asn_data = data.get("asn") or {}
                    company_data = data.get("company") or {}
                    conn_data = data.get("connection") or {}

                    isp_name = (
                        (asn_data.get("name") if isinstance(asn_data, dict) else None)
                        or (company_data.get("name") if isinstance(company_data, dict) else None)
                        or (conn_data.get("isp_name") if isinstance(conn_data, dict) else None)
                    )
                    result["isp"] = isp_name
                    result["organization"] = isp_name

                    asn_num = (
                        (asn_data.get("asn") if isinstance(asn_data, dict) else None)
                        or (conn_data.get("autonomous_system_number") if isinstance(conn_data, dict) else None)
                    )
                    if asn_num:
                        result["asn"] = f"AS{asn_num} {isp_name}".strip() if isp_name else f"AS{asn_num}"

                    # 4. Security & Anonymity Flags
                    sec_data = data.get("security") or {}
                    if isinstance(sec_data, dict):
                        result["is_vpn"] = bool(sec_data.get("is_vpn"))
                        result["is_tor"] = bool(sec_data.get("is_tor"))
                        result["is_proxy"] = bool(sec_data.get("is_proxy"))
                        result["is_datacenter"] = bool(sec_data.get("is_hosting") or sec_data.get("is_datacenter"))
                        result["is_abuse"] = bool(sec_data.get("is_abuse"))
                        result["threat_level"] = "high" if (result["is_tor"] or result["is_abuse"]) else ("medium" if result["is_vpn"] else None)


                elif resp.status_code in (401, 403):
                    logger.warning("Abstract IP API unauthorized (%s) for %s - check API key", resp.status_code, val.address)
                    result["error"] = "Invalid or unverified API key"
                    result["error_code"] = resp.status_code
                elif resp.status_code == 429:
                    logger.warning("Abstract IP API rate limit (429) for %s", val.address)
                    result["error"] = "Rate limit exceeded"
                    result["error_code"] = 429
                else:
                    logger.warning("Abstract IP API error HTTP %s for %s", resp.status_code, val.address)
                    result["error"] = f"HTTP {resp.status_code}"
                    result["error_code"] = resp.status_code


        except httpx.TimeoutException:
            logger.warning("Abstract IP API request timeout for %s", val.address)
            result["error"] = "Timeout"
            result["error_code"] = "timeout"
        except Exception as exc:
            logger.warning("Abstract IP API query error for %s: %s", val.address, exc)
            result["error"] = str(exc)
            result["error_code"] = "provider_error"

        return result
