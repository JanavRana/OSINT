"""
normalizers/ip/normalizer.py

IP Geolocation normalizer — converts the IpGeolocationConnector's raw dict
into normalized facts following the shared internal schema (M3, Section 11.3
of MASTER_DESIGN.md).

Confidence assignments (NFR4 — explainability):

    IP (the address itself, valid)               → 1.00
    IP (private/reserved — informational only)   → 0.90
    LOCATION (geolocation country — estimate)    → 0.60
    LOCATION (geolocation region/city — estimate)→ 0.55
    CONTACT_INFO (ISP/org — registry record)     → 0.70
    GENERIC (ASN — registry record)              → 0.75
    GENERIC (timezone — geo-derived estimate)    → 0.60

IMPORTANT — Labelling requirements:
    ALL geolocation-derived facts MUST be labelled as "IP geolocation estimate"
    in their metadata. This is NOT confirmed physical location data.
    It is an approximate geographic region derived from IP registry records
    (ARIN, RIPE, APNIC, etc.), which:
      - May be off by hundreds of kilometres for mobile/satellite IPs
      - Reflects where the ISP's network block was registered, NOT where the
        subscriber is physically located at any given time
      - Changes over time as IPs are reassigned between ISPs

    Do NOT use language implying: exact location, a specific person's address,
    or permanent ownership by any individual.

Reverse DNS facts are produced by the existing ReverseDnsNormalizer,
not by this normalizer — do not duplicate that logic here.
"""

from __future__ import annotations

from typing import Any, ClassVar, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class IpGeolocationNormalizer(BaseNormalizer):
    """
    Normalizer for the 'ip_geolocation' connector's raw payload.

    Extracts one or more NormalizedFact instances from the structured
    dict produced by IpGeolocationConnector.fetch():

        - IP fact:           the IP address itself (with version/private flags)
        - LOCATION facts:    geolocation country and region/city (estimates only)
        - CONTACT_INFO fact: ISP/organization name from IP registry
        - GENERIC facts:     ASN number, timezone estimate
    """

    connector_name: ClassVar[str] = "ip_geolocation"

    # ── Confidence constants ───────────────────────────────────────────────
    # These are named and documented so that downstream consumers can
    # understand exactly why each fact has a particular confidence level
    # (NFR4: explainability / auditability).
    _CONF_IP_VALID: float = 1.00         # IP address structurally valid
    _CONF_IP_PRIVATE: float = 0.90       # Private/reserved IP (informational)
    _CONF_GEO_COUNTRY: float = 0.60      # Country from IP geolocation estimate
    _CONF_GEO_REGION: float = 0.55       # Region/city — more granular, less reliable
    _CONF_ISP: float = 0.70              # ISP/org name from IP registry record
    _CONF_ASN: float = 0.75             # ASN — stable registry record
    _CONF_TIMEZONE: float = 0.60         # Timezone derived from geo estimate

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert IpGeolocationConnector's raw dict into normalized facts.

        Args:
            raw_payload: The dict returned by IpGeolocationConnector.fetch().

        Returns:
            A list of NormalizedFact instances. At minimum, one IP fact is
            always produced (even for private/error cases) to preserve the
            audit trail. Geolocation facts are omitted when unavailable.

        Raises:
            NormalizationError: If raw_payload is not a dict at all.
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )

        facts: List[NormalizedFact] = []

        ip_addr = raw_payload.get("ip", "")
        version = raw_payload.get("version")
        is_private = raw_payload.get("is_private", False)
        is_loopback = raw_payload.get("is_loopback", False)
        is_link_local = raw_payload.get("is_link_local", False)
        is_reserved = raw_payload.get("is_reserved", False)
        is_publicly_routable = raw_payload.get("is_publicly_routable", False)
        error = raw_payload.get("error")
        error_code = raw_payload.get("error_code")

        # ── 1. Primary IP fact ─────────────────────────────────────────────
        # Always produced — even for private/invalid IPs — to maintain the
        # audit trail of the investigation attempt (NFR9).
        if error_code == "validation_error":
            # The address itself was malformed; record with near-zero confidence
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=ip_addr or "invalid",
                    source_connector=self.connector_name,
                    confidence=0.10,
                    metadata={
                        "field": "ip_address",
                        "error": error,
                        "validation_failed": True,
                    },
                )
            )
            return facts  # No further facts possible

        # Private / reserved IP — record the IP itself but skip geo
        if not is_publicly_routable and ip_addr:
            ip_class = (
                "loopback" if is_loopback else
                "link-local" if is_link_local else
                "private" if is_private else
                "reserved"
            )
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=ip_addr,
                    source_connector=self.connector_name,
                    confidence=self._CONF_IP_PRIVATE,
                    metadata={
                        "field": "ip_address",
                        "version": version,
                        "ip_class": ip_class,
                        "note": (
                            f"This is a {ip_class} IP address. "
                            "No geolocation data is available for non-public IPs."
                        ),
                    },
                )
            )
            return facts  # Geolocation not applicable

        if ip_addr:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=ip_addr,
                    source_connector=self.connector_name,
                    confidence=self._CONF_IP_VALID,
                    metadata={
                        "field": "ip_address",
                        "version": version,
                        "is_publicly_routable": is_publicly_routable,
                    },
                )
            )

        # If geolocation lookup failed entirely but we have a valid IP,
        # still return the IP fact; skip the rest.
        if error and not raw_payload.get("country"):
            return facts

        # ── 2. LOCATION — Country (geo estimate) ──────────────────────────
        country_fact = self._build_country_fact(raw_payload)
        if country_fact:
            facts.append(country_fact)

        # ── 3. LOCATION — Region / City (geo estimate) ────────────────────
        region_fact = self._build_region_fact(raw_payload)
        if region_fact:
            facts.append(region_fact)

        # ── 4. CONTACT_INFO — ISP / Organization ──────────────────────────
        isp_fact = self._build_isp_fact(raw_payload)
        if isp_fact:
            facts.append(isp_fact)

        # ── 5. GENERIC — ASN ──────────────────────────────────────────────
        asn_fact = self._build_asn_fact(raw_payload)
        if asn_fact:
            facts.append(asn_fact)

        # ── 6. GENERIC — Timezone (geo-derived estimate) ──────────────────
        tz_fact = self._build_timezone_fact(raw_payload)
        if tz_fact:
            facts.append(tz_fact)

        return facts

    # ── Private builders ───────────────────────────────────────────────────

    def _build_country_fact(
        self, payload: dict
    ) -> Optional[NormalizedFact]:
        """Build a LOCATION fact for the country-level geolocation estimate."""
        country = payload.get("country")
        country_code = payload.get("country_code")
        if not country and not country_code:
            return None

        value = country or country_code
        return NormalizedFact(
            fact_type=FactType.LOCATION,
            value=value,
            source_connector=self.connector_name,
            confidence=self._CONF_GEO_COUNTRY,
            metadata={
                "field": "country",
                "country": country,
                "country_code": country_code,
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                # IMPORTANT: this label is mandatory per spec
                "data_label": "IP geolocation estimate",
                "note": (
                    "Country is an approximate geolocation estimate based on "
                    "IP registry records. It does NOT represent the physical "
                    "location of any specific person or device."
                ),
            },
        )

    def _build_region_fact(
        self, payload: dict
    ) -> Optional[NormalizedFact]:
        """Build a LOCATION fact for the region/city-level geolocation estimate."""
        region = payload.get("region")
        city = payload.get("city")
        if not region and not city:
            return None

        parts = [p for p in [city, region] if p]
        value = ", ".join(parts)
        return NormalizedFact(
            fact_type=FactType.LOCATION,
            value=value,
            source_connector=self.connector_name,
            confidence=self._CONF_GEO_REGION,
            metadata={
                "field": "region_city",
                "region": region,
                "city": city,
                "data_label": "IP geolocation estimate",
                "note": (
                    "Region and city are approximate geolocation estimates. "
                    "Granularity varies widely — accuracy for mobile/satellite "
                    "IPs may be off by hundreds of kilometres."
                ),
            },
        )

    def _build_isp_fact(
        self, payload: dict
    ) -> Optional[NormalizedFact]:
        """Build a CONTACT_INFO fact for the ISP/organization name."""
        org = payload.get("org")
        if not org:
            return None

        # Strip ASN prefix if present (e.g. "AS15169 Google LLC" → "Google LLC")
        display_org = org
        if " " in org and org.split()[0].startswith("AS") and org.split()[0][2:].isdigit():
            display_org = " ".join(org.split()[1:])

        return NormalizedFact(
            fact_type=FactType.CONTACT_INFO,
            value=display_org,
            source_connector=self.connector_name,
            confidence=self._CONF_ISP,
            metadata={
                "field": "isp_org",
                "raw_org": org,
                "note": (
                    "ISP/organization is from IP registry records (ARIN/RIPE/APNIC). "
                    "This is the network owner, NOT necessarily the device user."
                ),
            },
        )

    def _build_asn_fact(
        self, payload: dict
    ) -> Optional[NormalizedFact]:
        """Build a GENERIC fact for the ASN (Autonomous System Number)."""
        asn = payload.get("asn")
        if not asn:
            return None

        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=asn,
            source_connector=self.connector_name,
            confidence=self._CONF_ASN,
            metadata={
                "field": "asn",
                "note": "ASN (Autonomous System Number) from IP registry records.",
            },
        )

    def _build_timezone_fact(
        self, payload: dict
    ) -> Optional[NormalizedFact]:
        """Build a GENERIC fact for the IANA timezone (geo-derived estimate)."""
        tz = payload.get("timezone")
        if not tz:
            return None

        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=tz,
            source_connector=self.connector_name,
            confidence=self._CONF_TIMEZONE,
            metadata={
                "field": "timezone",
                "inferred": True,
                "data_label": "IP geolocation estimate",
                "note": (
                    "Timezone is derived from the IP's geolocation estimate. "
                    "It is approximate and may not reflect the actual timezone "
                    "of the device or its user."
                ),
            },
        )
