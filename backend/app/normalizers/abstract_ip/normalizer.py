"""
normalizers/abstract_ip/normalizer.py

Abstract IP Normalizer.

Transforms raw Abstract API payload into normalized facts, emphasizing
security and anonymity risk flags (VPN, Tor, Proxy, Datacenter, Threat Level).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact



logger = logging.getLogger("osint-aggregator")


@normalizer_registry.register
class AbstractIpNormalizer(BaseNormalizer):
    """
    Normalizer for Abstract IP Geolocation & Anonymity API payload.
    """

    connector_name: ClassVar[str] = "abstract_ip"

    def normalize(self, raw_data: Any) -> List[NormalizedFact]:
        """
        Transform raw Abstract IP dict payload into normalized facts.
        """
        if not isinstance(raw_data, dict):
            raise NormalizationError(
                f"AbstractIpNormalizer expected dict, got {type(raw_data).__name__}"
            )

        facts: List[NormalizedFact] = []

        # Handle skipped or unroutable IPs
        if not raw_data.get("is_publicly_routable"):
            return facts

            return facts

        if raw_data.get("error"):
            logger.info("Abstract IP payload contains error '%s'; returning base IP fact.", raw_data.get("error"))
            return facts

        # 2. Security & Anonymity Risk Flags (Key OSINT Data)
        is_vpn = raw_data.get("is_vpn")
        is_tor = raw_data.get("is_tor")
        is_proxy = raw_data.get("is_proxy")
        is_datacenter = raw_data.get("is_datacenter")
        threat_level = raw_data.get("threat_level")

        if is_tor:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value="ACTIVE TOR EXIT NODE",
                    confidence=0.98,
                    metadata={
                        "field": "tor_exit_node",
                        "is_tor": True,
                        "risk_level": "CRITICAL",
                        "data_label": "Tor Exit Node",
                        "note": "IP is an active Tor Exit Node. Physical location data is proxied.",
                    },
                )
            )

        if is_vpn:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value="COMMERCIAL VPN DETECTED",
                    confidence=0.95,
                    metadata={
                        "field": "vpn_detected",
                        "is_vpn": True,
                        "risk_level": "HIGH",
                        "data_label": "Commercial VPN",
                        "note": "IP is associated with a commercial VPN provider (NordVPN, ExpressVPN, Mullvad, etc.).",
                    },
                )
            )

        if is_proxy:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value="OPEN / SOCKS PROXY DETECTED",
                    confidence=0.90,
                    metadata={
                        "field": "proxy_detected",
                        "is_proxy": True,
                        "risk_level": "HIGH",
                        "data_label": "Proxy Server",
                        "note": "IP is a known HTTP/SOCKS proxy server.",
                    },
                )
            )

        if is_datacenter:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value="DATACENTER / HOSTING IP",
                    confidence=0.90,
                    metadata={
                        "field": "datacenter_ip",
                        "is_datacenter": True,
                        "risk_level": "MEDIUM",
                        "data_label": "Datacenter IP",
                        "note": "IP belongs to a cloud hosting/datacenter provider (AWS, DigitalOcean, Hetzner, etc.).",
                    },
                )
            )

        if threat_level and str(threat_level).lower() != "low":
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value=f"THREAT RATING: {str(threat_level).upper()}",
                    confidence=0.85,
                    metadata={
                        "field": "threat_level",
                        "threat_level": str(threat_level).upper(),
                        "note": "Threat level calculated by Abstract Security Intelligence.",
                    },
                )
            )

        # 3. Country Geolocation
        country = raw_data.get("country")
        if country and isinstance(country, str) and country.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.LOCATION,
                    value=country.strip(),
                    confidence=0.80,
                    metadata={
                        "field": "country",
                        "country": country.strip(),
                        "country_code": raw_data.get("country_code"),
                        "latitude": raw_data.get("latitude"),
                        "longitude": raw_data.get("longitude"),
                        "data_label": "Abstract IP Geolocation",
                    },
                )
            )

        # 4. Region & City
        city = raw_data.get("city")
        region = raw_data.get("region")
        if city or region:
            parts = [p for p in [city, region] if p and isinstance(p, str) and p.strip()]
            location_val = ", ".join(parts)
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.LOCATION,
                    value=location_val,
                    confidence=0.75,
                    metadata={
                        "field": "region_city",
                        "city": city,
                        "region": region,
                        "postal_code": raw_data.get("postal_code"),
                        "data_label": "Abstract IP Geolocation",
                    },
                )
            )

        # 5. ISP & Organization
        isp = raw_data.get("isp")
        org = raw_data.get("organization")
        isp_val = isp or org
        if isp_val and isinstance(isp_val, str) and isp_val.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.CONTACT_INFO,
                    value=isp_val.strip(),
                    confidence=0.85,
                    metadata={
                        "field": "isp_org",
                        "isp": isp,
                        "organization": org,
                    },
                )
            )

        # 6. ASN
        asn = raw_data.get("asn")
        if asn and isinstance(asn, str) and asn.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value=asn.strip(),
                    confidence=0.90,
                    metadata={
                        "field": "asn",
                    },
                )
            )

        # 7. Timezone
        timezone_name = raw_data.get("timezone")
        if timezone_name and isinstance(timezone_name, str) and timezone_name.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value=timezone_name.strip(),
                    confidence=0.80,
                    metadata={
                        "field": "timezone",
                        "gmt_offset": raw_data.get("gmt_offset"),
                    },
                )
            )

        return facts
