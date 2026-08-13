"""
normalizers/mac/normalizer.py

MAC Address & Wi-Fi BSSID normalizer.

Converts MacOsintConnector raw payload into normalized facts following
the shared internal schema (M3, Section 11.3 of MASTER_DESIGN.md).

Confidence assignments:
    GENERIC (normalized MAC address)          → 1.00
    ORGANIZATION (Hardware Vendor/OUI)        → 0.90
    LOCATION (Wigle.net Wi-Fi BSSID GPS)      → 0.75
    GENERIC (Wi-Fi SSID network name)         → 0.85
    GENERIC (Security protocol / Channel)     → 0.80
"""

from __future__ import annotations

from typing import Any, ClassVar, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class MacNormalizer(BaseNormalizer):
    """
    Normalizer for the 'mac_osint' connector's raw payload.

    Extracts:
        - GENERIC fact: MAC address itself
        - ORGANIZATION fact: Hardware Vendor / Manufacturer name
        - LOCATION facts: Wi-Fi GPS location from Wigle.net
        - GENERIC facts: Wi-Fi SSID network name, channel, encryption
    """

    connector_name: ClassVar[str] = "mac_osint"

    _CONF_MAC_VALID: float = 1.00       # Structurally valid MAC
    _CONF_VENDOR: float = 0.90          # IEEE OUI registry match
    _CONF_WIGLE_GEO: float = 0.75       # Wigle.net Wi-Fi GPS match
    _CONF_SSID: float = 0.85            # Wi-Fi network name
    _CONF_WIFI_META: float = 0.80       # Channel / Encryption protocol

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert MacOsintConnector's raw payload into normalized facts.
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )

        facts: List[NormalizedFact] = []

        mac_str = raw_payload.get("normalized_mac") or raw_payload.get("mac", "")
        vendor = raw_payload.get("vendor")
        error = raw_payload.get("error")
        error_code = raw_payload.get("error_code")

        # Skip if input was skipped (e.g. non-MAC input passed under IP identifier)
        if error_code == "skipped":
            return facts

        # Handle validation error
        if error_code == "validation_error":
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=mac_str or "invalid",
                    source_connector=self.connector_name,
                    confidence=0.10,
                    metadata={
                        "field": "mac_address",
                        "error": error,
                        "validation_failed": True,
                    },
                )
            )
            return facts

        # ── 1. Primary MAC address fact ────────────────────────────────────
        if mac_str:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=mac_str,
                    source_connector=self.connector_name,
                    confidence=self._CONF_MAC_VALID,
                    metadata={
                        "field": "mac_address",
                        "oui_prefix": raw_payload.get("oui_prefix"),
                        "is_multicast": raw_payload.get("is_multicast"),
                        "is_locally_administered": raw_payload.get("is_locally_administered"),
                    },
                )
            )

        # ── 2. Hardware Vendor / Manufacturer ─────────────────────────────
        if vendor and vendor != "Unknown Hardware Vendor":
            facts.append(
                NormalizedFact(
                    fact_type=FactType.ORGANIZATION,
                    value=vendor,
                    source_connector=self.connector_name,
                    confidence=self._CONF_VENDOR,
                    metadata={
                        "field": "hardware_vendor",
                        "oui_prefix": raw_payload.get("oui_prefix"),
                        "note": "Hardware vendor identified from IEEE OUI registry.",
                    },
                )
            )

        # ── 3. Wigle.net Wi-Fi Location ────────────────────────────────────
        if raw_payload.get("wigle_matched"):
            lat = raw_payload.get("latitude")
            lon = raw_payload.get("longitude")
            city = raw_payload.get("city")
            country = raw_payload.get("country")
            region = raw_payload.get("region")

            location_parts = [p for p in [city, region, country] if p]
            city_str = ", ".join(location_parts) if location_parts else ""
            gps_str = f"Lat: {lat}, Lon: {lon}"
            loc_str = f"{gps_str} ({city_str})" if city_str else gps_str


            facts.append(
                NormalizedFact(
                    fact_type=FactType.LOCATION,
                    value=loc_str,
                    source_connector=self.connector_name,
                    confidence=self._CONF_WIGLE_GEO,
                    metadata={
                        "field": "wifi_location",
                        "latitude": lat,
                        "longitude": lon,
                        "city": city,
                        "region": region,
                        "country": country,
                        "data_label": "Wigle Wi-Fi BSSID Geolocation",
                        "note": "Wi-Fi access point street location matched via Wigle.net.",
                    },
                )
            )

            # Wi-Fi Network Name (SSID)
            ssid = raw_payload.get("ssid")
            if ssid:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.GENERIC,
                        value=ssid,
                        source_connector=self.connector_name,
                        confidence=self._CONF_SSID,
                        metadata={
                            "field": "wifi_ssid",
                            "note": "Wi-Fi network name (SSID) associated with BSSID.",
                        },
                    )
                )

            # Encryption / Security Protocol
            encryption = raw_payload.get("encryption")
            if encryption:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.GENERIC,
                        value=encryption,
                        source_connector=self.connector_name,
                        confidence=self._CONF_WIFI_META,
                        metadata={
                            "field": "wifi_security",
                            "channel": raw_payload.get("channel"),
                        },
                    )
                )

        return facts
