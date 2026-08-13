"""
connectors/mac/connector.py

MAC Address & Wi-Fi BSSID OSINT connector.

This connector:
1. Subclasses BaseConnector and registers via @registry.register.
2. Accepts MAC or IP identifiers (if a MAC format is supplied under IP/MAC).
3. Validates the MAC address (supports colon, hyphen, dot, bare hex formats).
4. Identifies the Hardware Manufacturer / Vendor using the OUI (Organizationally
   Unique Identifier) via maclookup API & built-in IEEE database.
5. If Wigle.net credentials (`WIGLE_API_NAME` & `WIGLE_API_TOKEN`) are configured
   in the environment, queries `https://wigle.net/api/v2/network/search?netid={mac}`
   to discover Wi-Fi access point BSSID location, SSID name, channel, and security.
6. Returns a raw JSON-serializable dictionary for downstream normalization (M3).
"""

from __future__ import annotations

import logging
import os
import base64
from typing import Any, ClassVar, Dict, FrozenSet, Optional

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import MacValidationError, validate_mac_address

logger = logging.getLogger(__name__)

# Built-in IEEE OUI database snippet for instant offline vendor lookup
_WELL_KNOWN_OUIS: Dict[str, str] = {
    "00:03:93": "Apple, Inc.",
    "00:05:02": "Apple, Inc.",
    "00:0A:95": "Apple, Inc.",
    "00:0D:93": "Apple, Inc.",
    "00:10:FA": "Apple, Inc.",
    "00:11:24": "Apple, Inc.",
    "00:14:51": "Apple, Inc.",
    "00:16:CB": "Apple, Inc.",
    "00:17:F2": "Apple, Inc.",
    "00:19:E3": "Apple, Inc.",
    "00:1B:63": "Apple, Inc.",
    "00:1C:B3": "Apple, Inc.",
    "00:1D:4F": "Apple, Inc.",
    "00:1E:52": "Apple, Inc.",
    "00:1F:5B": "Apple, Inc.",
    "00:1F:F3": "Apple, Inc.",
    "00:21:E9": "Apple, Inc.",
    "00:22:41": "Apple, Inc.",
    "00:23:12": "Apple, Inc.",
    "00:23:32": "Apple, Inc.",
    "00:23:6C": "Apple, Inc.",
    "00:24:36": "Apple, Inc.",
    "00:25:00": "Apple, Inc.",
    "00:25:4B": "Apple, Inc.",
    "00:26:08": "Apple, Inc.",
    "00:26:4A": "Apple, Inc.",
    "00:26:BB": "Apple, Inc.",
    "00:26:B0": "Apple, Inc.",
    "00:00:0C": "Cisco Systems, Inc.",
    "00:01:42": "Cisco Systems, Inc.",
    "00:01:43": "Cisco Systems, Inc.",
    "00:01:96": "Cisco Systems, Inc.",
    "00:01:97": "Cisco Systems, Inc.",
    "00:02:16": "Cisco Systems, Inc.",
    "00:02:17": "Cisco Systems, Inc.",
    "00:02:4A": "Cisco Systems, Inc.",
    "00:02:4B": "Cisco Systems, Inc.",
    "00:02:B9": "Cisco Systems, Inc.",
    "00:02:BA": "Cisco Systems, Inc.",
    "00:02:FC": "Cisco Systems, Inc.",
    "00:03:31": "Cisco Systems, Inc.",
    "00:03:32": "Cisco Systems, Inc.",
    "00:03:6B": "Cisco Systems, Inc.",
    "00:03:6C": "Cisco Systems, Inc.",
    "00:03:E3": "Cisco Systems, Inc.",
    "00:03:E4": "Cisco Systems, Inc.",
    "00:04:27": "Cisco Systems, Inc.",
    "00:04:28": "Cisco Systems, Inc.",
    "00:04:4D": "Cisco Systems, Inc.",
    "00:04:4E": "Cisco Systems, Inc.",
    "00:04:9A": "Cisco Systems, Inc.",
    "00:04:9B": "Cisco Systems, Inc.",
    "00:04:C0": "Cisco Systems, Inc.",
    "00:04:C1": "Cisco Systems, Inc.",
    "00:04:DD": "Cisco Systems, Inc.",
    "00:04:DE": "Cisco Systems, Inc.",
    "00:05:31": "Cisco Systems, Inc.",
    "00:05:32": "Cisco Systems, Inc.",
    "00:05:73": "Cisco Systems, Inc.",
    "00:05:74": "Cisco Systems, Inc.",
    "00:05:9A": "Cisco Systems, Inc.",
    "00:05:9B": "Cisco Systems, Inc.",
    "00:05:DC": "Cisco Systems, Inc.",
    "00:05:DD": "Cisco Systems, Inc.",
    "00:02:B3": "Intel Corporation",
    "00:03:47": "Intel Corporation",
    "00:04:23": "Intel Corporation",
    "00:0E:0C": "Intel Corporation",
    "00:13:02": "Intel Corporation",
    "00:13:20": "Intel Corporation",
    "00:13:CE": "Intel Corporation",
    "00:13:E8": "Intel Corporation",
    "00:15:00": "Intel Corporation",
    "00:16:6F": "Intel Corporation",
    "00:16:EA": "Intel Corporation",
    "00:18:DE": "Intel Corporation",
    "00:19:D1": "Intel Corporation",
    "00:1B:21": "Intel Corporation",
    "00:1C:BF": "Intel Corporation",
    "00:1D:E0": "Intel Corporation",
    "00:1E:64": "Intel Corporation",
    "00:1F:3C": "Intel Corporation",
    "00:21:5C": "Intel Corporation",
    "00:21:6A": "Intel Corporation",
    "00:22:FB": "Intel Corporation",
    "00:23:14": "Intel Corporation",
    "00:23:4D": "Intel Corporation",
    "00:24:D6": "Intel Corporation",
    "00:24:D7": "Intel Corporation",
    "00:26:C6": "Intel Corporation",
    "00:26:C7": "Intel Corporation",
    "00:00:F0": "Samsung Electronics Co.,Ltd",
    "00:02:78": "Samsung Electronics Co.,Ltd",
    "00:07:AB": "Samsung Electronics Co.,Ltd",
    "00:09:18": "Samsung Electronics Co.,Ltd",
    "00:0D:AE": "Samsung Electronics Co.,Ltd",
    "00:0E:6D": "Samsung Electronics Co.,Ltd",
    "00:12:47": "Samsung Electronics Co.,Ltd",
    "00:12:FB": "Samsung Electronics Co.,Ltd",
    "00:13:77": "Samsung Electronics Co.,Ltd",
    "00:15:99": "Samsung Electronics Co.,Ltd",
    "00:15:B9": "Samsung Electronics Co.,Ltd",
    "00:16:6C": "Samsung Electronics Co.,Ltd",
    "00:16:DB": "Samsung Electronics Co.,Ltd",
    "00:17:C9": "Samsung Electronics Co.,Ltd",
    "00:17:D5": "Samsung Electronics Co.,Ltd",
    "00:18:AF": "Samsung Electronics Co.,Ltd",
    "00:1A:8A": "Samsung Electronics Co.,Ltd",
    "00:1B:98": "Samsung Electronics Co.,Ltd",
    "00:1C:43": "Samsung Electronics Co.,Ltd",
    "00:1D:25": "Samsung Electronics Co.,Ltd",
    "00:1D:F6": "Samsung Electronics Co.,Ltd",
    "00:1E:7D": "Samsung Electronics Co.,Ltd",
    "00:1E:E1": "Samsung Electronics Co.,Ltd",
    "00:1F:CC": "Samsung Electronics Co.,Ltd",
    "00:21:19": "Samsung Electronics Co.,Ltd",
    "00:21:D1": "Samsung Electronics Co.,Ltd",
    "00:21:D2": "Samsung Electronics Co.,Ltd",
    "00:23:39": "Samsung Electronics Co.,Ltd",
    "00:23:99": "Samsung Electronics Co.,Ltd",
    "00:24:54": "Samsung Electronics Co.,Ltd",
    "00:24:91": "Samsung Electronics Co.,Ltd",
    "00:24:E9": "Samsung Electronics Co.,Ltd",
    "00:25:66": "Samsung Electronics Co.,Ltd",
    "00:25:67": "Samsung Electronics Co.,Ltd",
    "00:26:37": "Samsung Electronics Co.,Ltd",
    "00:26:5D": "Samsung Electronics Co.,Ltd",
    "00:26:C0": "Samsung Electronics Co.,Ltd",
    "00:14:6C": "NETGEAR, Inc.",
    "00:18:4D": "NETGEAR, Inc.",
    "00:1F:33": "NETGEAR, Inc.",
    "00:22:3F": "NETGEAR, Inc.",
    "00:24:B2": "NETGEAR, Inc.",
    "00:26:F2": "NETGEAR, Inc.",
    "00:04:0E": "ASUSTek COMPUTER INC.",
    "00:0E:A6": "ASUSTek COMPUTER INC.",
    "00:11:D8": "ASUSTek COMPUTER INC.",
    "00:13:D4": "ASUSTek COMPUTER INC.",
    "00:15:F2": "ASUSTek COMPUTER INC.",
    "00:17:31": "ASUSTek COMPUTER INC.",
    "00:18:F3": "ASUSTek COMPUTER INC.",
    "00:1A:92": "ASUSTek COMPUTER INC.",
    "00:1B:FC": "ASUSTek COMPUTER INC.",
    "00:1D:60": "ASUSTek COMPUTER INC.",
    "00:1E:8C": "ASUSTek COMPUTER INC.",
    "00:1F:C6": "ASUSTek COMPUTER INC.",
    "00:22:15": "ASUSTek COMPUTER INC.",
    "00:23:54": "ASUSTek COMPUTER INC.",
    "00:24:8C": "ASUSTek COMPUTER INC.",
    "00:26:18": "ASUSTek COMPUTER INC.",
    "00:14:D1": "TP-Link Corporation Limited",
    "00:19:E0": "TP-Link Corporation Limited",
    "00:1D:0F": "TP-Link Corporation Limited",
    "00:21:27": "TP-Link Corporation Limited",
    "00:23:CD": "TP-Link Corporation Limited",
    "00:25:86": "TP-Link Corporation Limited",
    "00:27:19": "TP-Link Corporation Limited",
    "00:50:56": "VMware, Inc.",
    "00:0C:29": "VMware, Inc.",
    "00:05:69": "VMware, Inc.",
    "08:00:27": "Oracle Corporation (VirtualBox)",
    "52:54:00": "QEMU / KVM Virtual NIC",
    "B8:27:EB": "Raspberry Pi Foundation",
    "DC:A6:32": "Raspberry Pi Foundation",
    "E4:5F:01": "Raspberry Pi Foundation",
}


@registry.register
class MacOsintConnector(BaseConnector):
    """
    MAC Address & Wi-Fi BSSID OSINT connector.

    Supports `IdentifierType.MAC` (and auto-detected MACs under `IdentifierType.IP`).
    Extracts OUI Hardware Vendor and queries Wigle.net Wi-Fi geolocation.
    """

    name: ClassVar[str] = "mac_osint"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.MAC, IdentifierType.IP}
    )
    timeout_seconds: ClassVar[float] = 15.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Validate MAC address, perform OUI vendor lookup, and query Wigle.net.
        """
        raw_value = identifier.value.strip()

        result: Dict[str, Any] = {
            "mac": raw_value,
            "normalized_mac": None,
            "oui_prefix": None,
            "vendor": None,
            "is_multicast": False,
            "is_locally_administered": False,
            "bssid": None,
            "ssid": None,
            "latitude": None,
            "longitude": None,
            "country": None,
            "region": None,
            "city": None,
            "channel": None,
            "encryption": None,
            "wigle_matched": False,
            "error": None,
            "error_code": None,
        }

        # ── 1. Validate MAC address ─────────────────────────────────────────
        try:
            validation = validate_mac_address(raw_value)
        except MacValidationError as exc:
            # If called under IP identifier type with non-MAC input, skip cleanly
            if identifier.type == IdentifierType.IP:
                result["error"] = f"Not a MAC address: {exc}"
                result["error_code"] = "skipped"
                return result
            result["error"] = str(exc)
            result["error_code"] = "validation_error"
            return result

        result["normalized_mac"] = validation.normalized
        result["oui_prefix"] = validation.oui_prefix
        result["is_multicast"] = validation.is_multicast
        result["is_locally_administered"] = validation.is_locally_administered

        # ── 2. OUI Vendor Lookup ───────────────────────────────────────────
        vendor = _WELL_KNOWN_OUIS.get(validation.oui_prefix)
        if not vendor:
            # Try maclookup API online
            vendor = await self._lookup_oui_online(validation.oui_prefix)
        result["vendor"] = vendor or "Unknown Hardware Vendor"

        # ── 3. Wigle.net Wi-Fi BSSID Geolocation (Optional Env Vars) ───────
        api_name = os.environ.get("WIGLE_API_NAME") or os.environ.get("WIGLE_API_KEY")
        api_token = os.environ.get("WIGLE_API_TOKEN")

        if api_name and api_token:
            wigle_data = await self._query_wigle(validation.normalized, api_name, api_token)
            if wigle_data.get("matched"):
                result["wigle_matched"] = True
                result["bssid"] = validation.normalized
                result["ssid"] = wigle_data.get("ssid")
                result["latitude"] = wigle_data.get("latitude")
                result["longitude"] = wigle_data.get("longitude")
                result["country"] = wigle_data.get("country")
                result["region"] = wigle_data.get("region")
                result["city"] = wigle_data.get("city")
                result["channel"] = wigle_data.get("channel")
                result["encryption"] = wigle_data.get("encryption")
        else:
            logger.info("WIGLE_API_NAME/TOKEN not configured; skipping Wigle Wi-Fi lookup.")

        return result

    async def _lookup_oui_online(self, oui_prefix: str) -> Optional[str]:
        """Query maclookup.app API for OUI prefix."""
        clean_prefix = oui_prefix.replace(":", "")
        url = f"https://api.maclookup.app/v2/macs/{clean_prefix}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    company = data.get("company")
                    if company and isinstance(company, str) and company.strip():
                        return company.strip()
        except Exception as exc:
            logger.warning("MAC OUI online lookup failed for %s: %s", oui_prefix, exc)
        return None

    async def _query_wigle(self, mac: str, api_name: str, api_token: str) -> Dict[str, Any]:
        """
        Query Wigle.net v2 network search endpoint.

        URL: https://wigle.net/api/v2/network/search?netid={mac}
        Auth: HTTP Basic Auth (api_name:api_token)
        """
        url = "https://api.wigle.net/api/v2/network/search"

        params = {"netid": mac}
        auth = (api_name.strip(), api_token.strip())
        headers = {"Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params, auth=auth, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results and isinstance(results, list):
                        top = results[0]
                        return {
                            "matched": True,
                            "ssid": top.get("ssid"),
                            "latitude": top.get("triglat") or top.get("lat"),
                            "longitude": top.get("triglon") or top.get("lon"),
                            "country": top.get("country"),
                            "region": top.get("region"),
                            "city": top.get("city"),
                            "channel": top.get("channel"),
                            "encryption": top.get("encryption"),
                        }
        except Exception as exc:
            logger.warning("Wigle.net query failed for %s: %s", mac, exc)

        return {"matched": False}
