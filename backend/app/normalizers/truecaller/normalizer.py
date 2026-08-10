"""
normalizers/truecaller/normalizer.py

Normalizer for raw responses produced by TruecallerConnector.

Transforms Truecaller JSON results into structured, typed NormalizedFact
objects for downstream identity graph linking:
    - Name (FactType.PROFILE_DATA) with confidence 0.85
    - Email (FactType.EMAIL) with confidence 0.90
    - Location/Address (FactType.LOCATION) with confidence 0.80
    - Carrier (FactType.CONTACT_INFO) with confidence 0.80
    - Spam Score / Badge (FactType.GENERIC) with confidence 0.70
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class TruecallerNormalizer(BaseNormalizer):
    """Normalizes raw payloads returned by TruecallerConnector into typed facts."""

    connector_name: ClassVar[str] = "truecaller"

    # Calibrated confidence scores for Truecaller findings
    _CONF_NAME = 0.85
    _CONF_EMAIL = 0.90
    _CONF_LOCATION = 0.80
    _CONF_CARRIER = 0.80
    _CONF_GENERIC = 0.70

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Extract facts from raw Truecaller response.

        Args:
            raw_payload: Dict returned by TruecallerConnector.fetch().

        Returns:
            List of NormalizedFact objects.
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                f"TruecallerNormalizer expected dict raw_payload, got {type(raw_payload).__name__}"
            )

        facts: List[NormalizedFact] = []

        # 1. Name Fact (PROFILE_DATA)
        name = raw_payload.get("name")
        if name and isinstance(name, str) and name.strip():
            facts.append(
                NormalizedFact(
                    fact_type=FactType.PROFILE_DATA,
                    value=name.strip(),
                    source_connector=self.connector_name,
                    confidence=self._CONF_NAME,
                    metadata={
                        "field": "name",
                        "full_name": name.strip(),
                        "source": "Truecaller",
                    },
                )
            )

        # 2. Email Fact (EMAIL)
        email = raw_payload.get("email")
        if email and isinstance(email, str) and email.strip():
            facts.append(
                NormalizedFact(
                    fact_type=FactType.EMAIL,
                    value=email.strip().lower(),
                    source_connector=self.connector_name,
                    confidence=self._CONF_EMAIL,
                    metadata={
                        "field": "email",
                        "source": "Truecaller",
                    },
                )
            )

        # 3. Location / Address Fact (LOCATION)
        city = raw_payload.get("city")
        state = raw_payload.get("state")
        country = raw_payload.get("country")
        address = raw_payload.get("address")

        location_parts = [p for p in [city, state, country] if p and isinstance(p, str)]
        if location_parts:
            loc_str = ", ".join(location_parts)
            facts.append(
                NormalizedFact(
                    fact_type=FactType.LOCATION,
                    value=loc_str,
                    source_connector=self.connector_name,
                    confidence=self._CONF_LOCATION,
                    metadata={
                        "field": "location",
                        "city": city,
                        "state": state,
                        "country": country,
                        "address": address,
                        "source": "Truecaller",
                    },
                )
            )

        # 4. Carrier Fact (CONTACT_INFO)
        carrier = raw_payload.get("carrier")
        if carrier and isinstance(carrier, str) and carrier.strip():
            facts.append(
                NormalizedFact(
                    fact_type=FactType.CONTACT_INFO,
                    value=carrier.strip(),
                    source_connector=self.connector_name,
                    confidence=self._CONF_CARRIER,
                    metadata={
                        "field": "carrier",
                        "carrier": carrier.strip(),
                        "source": "Truecaller",
                    },
                )
            )

        # 5. Badge / Spam Fact (GENERIC)
        badge = raw_payload.get("badge")
        if badge:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=str(badge),
                    source_connector=self.connector_name,
                    confidence=self._CONF_GENERIC,
                    metadata={
                        "field": "badge",
                        "badge": badge,
                        "source": "Truecaller",
                    },
                )
            )

        return facts
