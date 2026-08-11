"""
connectors/ip/connector.py

IP Geolocation OSINT connector.

This connector:
1. Subclasses BaseConnector and registers via @registry.register.
2. Accepts only IP identifiers.
3. Validates the IP (IPv4, IPv6, private/reserved detection) using the
   stdlib ipaddress module — zero external dependencies for validation.
4. Queries ipapi.co for geolocation and network metadata using httpx.
5. Returns a raw JSON-serializable dict for downstream normalization (M3).
6. Does NOT normalize data itself.
7. Does NOT access the database.

API used: https://ipapi.co/{ip}/json/
- Free tier: ~30,000 requests/month (no API key required for basic use).
- API key (optional): set IP_GEOLOCATION_API_KEY env var if you have a
  paid plan; the connector appends it as a `?key=` query parameter.
- Do NOT hardcode any API key. Read from environment only.

IMPORTANT — Responsible-use boundary (MASTER_DESIGN.md §4.3):
    IP geolocation is an APPROXIMATE network-level estimate only.
    It indicates the rough geographic area associated with the IP
    block according to ARIN/RIPE/APNIC registry records — NOT the
    physical location of any person. The normalizer (M3) labels all
    geolocation facts as "IP geolocation estimate" and assigns a
    reduced confidence score to reflect this uncertainty.

Failure isolation:
    A failed or timed-out geolocation lookup MUST NOT prevent reverse DNS
    from running. Each connector runs independently via the pipeline
    (ConnectorExecutionService / investigation_service.execute_investigation).
    This connector only handles geolocation; reverse DNS runs in its own
    separate ReverseDnsConnector.
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar, Dict, FrozenSet, Optional

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import IpValidationError, validate_ip_address

logger = logging.getLogger(__name__)

# Base URL for the ipapi.co public geolocation API
_IPAPI_BASE = "https://ipapi.co"


@registry.register
class IpGeolocationConnector(BaseConnector):
    """
    IP Geolocation OSINT connector using the ipapi.co public API.

    Retrieves, where available:
        - Country and country code
        - Region / state
        - City
        - Latitude / longitude
        - Timezone (IANA)
        - ASN
        - ISP / organization

    Also validates the IP and records private/reserved/loopback status
    in the raw payload so the normalizer can handle those cases cleanly.

    All geolocation data is labelled as an estimate in the raw payload;
    the normalizer converts this into appropriately-labelled facts with
    a reduced confidence score (0.60).
    """

    name: ClassVar[str] = "ip_geolocation"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.IP}
    )
    # ipapi.co typically responds in <1 s; 20 s gives ample headroom on a
    # slow connection or rate-limited response without blocking the pipeline.
    timeout_seconds: ClassVar[float] = 20.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Validate the IP address and query ipapi.co for geolocation data.

        Returns a JSON-serializable dict with:
            ip            — the normalized IP string
            version       — 4 or 6
            is_private    — True if RFC 1918 / loopback / link-local / reserved
            is_loopback   — True if 127.0.0.1 / ::1
            country       — full country name, or None
            country_code  — ISO-3166-1 alpha-2, or None
            region        — region/state name, or None
            city          — city name, or None
            latitude      — float, or None
            longitude     — float, or None
            timezone      — IANA timezone string, or None
            asn           — ASN string (e.g. "AS15169"), or None
            org           — ISP/org name, or None
            error         — error string if lookup failed, else None
            error_code    — numeric HTTP status or "validation_error", or None
        """
        raw_value = identifier.value.strip()

        base_result: Dict[str, Any] = {
            "ip": raw_value,
            "version": None,
            "is_private": False,
            "is_loopback": False,
            "is_link_local": False,
            "is_reserved": False,
            "is_publicly_routable": False,
            "country": None,
            "country_code": None,
            "region": None,
            "city": None,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "asn": None,
            "org": None,
            "error": None,
            "error_code": None,
        }

        # ── 1. Validate IP ─────────────────────────────────────────────────
        try:
            validation = validate_ip_address(raw_value)
        except IpValidationError as exc:
            base_result["error"] = str(exc)
            base_result["error_code"] = "validation_error"
            logger.warning("IP validation failed for '%s': %s", raw_value, exc)
            return base_result

        base_result["ip"] = validation.address  # Use normalized form
        base_result["version"] = validation.version
        base_result["is_private"] = validation.is_private
        base_result["is_loopback"] = validation.is_loopback
        base_result["is_link_local"] = validation.is_link_local
        base_result["is_reserved"] = validation.is_reserved
        base_result["is_publicly_routable"] = validation.is_publicly_routable

        # ── 2. Skip geolocation for non-public IPs ─────────────────────────
        if not validation.is_publicly_routable:
            reason = (
                "loopback" if validation.is_loopback else
                "link-local" if validation.is_link_local else
                "private" if validation.is_private else
                "reserved"
            )
            base_result["error"] = (
                f"{validation.address} is a {reason} IP address. "
                "Geolocation is only available for publicly routable IPs."
            )
            logger.info(
                "Skipping geolocation for %s IP: %s",
                reason, validation.address,
            )
            return base_result

        # ── 3. Query primary provider (ipapi.co) ───────────────────────────
        api_key: Optional[str] = os.environ.get("IP_GEOLOCATION_API_KEY") or None
        url = f"{_IPAPI_BASE}/{validation.address}/json/"
        params: Dict[str, str] = {}
        if api_key:
            params["key"] = api_key

        data: Dict[str, Any] = {}
        ipapi_success = False

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    try:
                        parsed = response.json()
                        if isinstance(parsed, dict) and not parsed.get("error"):
                            data = parsed
                            ipapi_success = True
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("ipapi.co request failed for %s: %s", validation.address, exc)

        # ── 4. Fallback provider (ip-api.com) if primary failed or rate-limited ─
        if not ipapi_success:
            logger.info("Trying secondary provider ip-api.com for %s...", validation.address)
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    fb_resp = await client.get(f"http://ip-api.com/json/{validation.address}")
                    if fb_resp.status_code == 200:
                        fb_data = fb_resp.json()
                        if fb_data.get("status") == "success":
                            base_result["country"] = fb_data.get("country") or None
                            base_result["country_code"] = fb_data.get("countryCode") or None
                            base_result["region"] = fb_data.get("regionName") or None
                            base_result["city"] = fb_data.get("city") or None
                            try:
                                base_result["latitude"] = float(fb_data.get("lat")) if fb_data.get("lat") is not None else None
                                base_result["longitude"] = float(fb_data.get("lon")) if fb_data.get("lon") is not None else None
                            except (TypeError, ValueError):
                                pass
                            base_result["timezone"] = fb_data.get("timezone") or None
                            base_result["asn"] = fb_data.get("as") or None
                            base_result["org"] = fb_data.get("isp") or fb_data.get("org") or None
                            base_result["error"] = None
                            base_result["error_code"] = None
                            logger.info("ip-api.com fallback succeeded for %s: city=%s, country=%s", validation.address, base_result["city"], base_result["country"])
                            return base_result
            except Exception as fb_exc:
                logger.warning("ip-api.com fallback failed for %s: %s", validation.address, fb_exc)

            # Both providers failed
            base_result["error"] = "IP geolocation providers rate limited or unavailable."
            base_result["error_code"] = "provider_error"
            return base_result

        # ── 5. Extract fields from primary ipapi.co response ───────────────
        base_result["country"] = data.get("country_name") or None
        base_result["country_code"] = data.get("country_code") or None
        base_result["region"] = data.get("region") or None
        base_result["city"] = data.get("city") or None

        try:
            lat = data.get("latitude")
            base_result["latitude"] = float(lat) if lat is not None else None
        except (TypeError, ValueError):
            base_result["latitude"] = None

        try:
            lon = data.get("longitude")
            base_result["longitude"] = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            base_result["longitude"] = None

        base_result["timezone"] = data.get("timezone") or None

        asn_raw = data.get("asn")
        if asn_raw:
            base_result["asn"] = str(asn_raw)
        else:
            asn_int = data.get("asn_id") or data.get("asn_num")
            base_result["asn"] = f"AS{asn_int}" if asn_int else None

        base_result["org"] = data.get("org") or None
        return base_result


