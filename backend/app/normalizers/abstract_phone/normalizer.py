"""
normalizers/abstract_phone/normalizer.py

Abstract Phone Validation Normalizer.

Transforms raw Abstract Phone payload into normalized facts, emphasizing
line-type classification (VoIP vs Mobile vs Landline), telecom carrier identification,
and geographic origin.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact

logger = logging.getLogger("osint-aggregator")


@normalizer_registry.register
class AbstractPhoneNormalizer(BaseNormalizer):
    """
    Normalizer for Abstract Phone Validation API payload.
    """

    connector_name: ClassVar[str] = "abstract_phone"

    def normalize(self, raw_data: Any) -> List[NormalizedFact]:
        """
        Transform raw Abstract Phone dict payload into normalized facts.
        """
        if not isinstance(raw_data, dict):
            raise NormalizationError(
                f"AbstractPhoneNormalizer expected dict, got {type(raw_data).__name__}"
            )

        facts: List[NormalizedFact] = []

        phone_val = (
            raw_data.get("international_format")
            or raw_data.get("cleaned_phone")
            or raw_data.get("phone")
            or ""
        )

        if raw_data.get("error") and not raw_data.get("abstract_matched"):
            logger.info("Abstract Phone payload contains error '%s'", raw_data.get("error"))
            return facts

        # 1. Base Phone Number fact
        if phone_val:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.PHONE,
                    value=phone_val,
                    confidence=1.00,
                    metadata={
                        "field": "phone_number",
                        "valid": raw_data.get("valid", False),
                        "local_format": raw_data.get("local_format"),
                        "international_format": raw_data.get("international_format"),
                    },
                )
            )

        # 2. Line Type Classification & VoIP Burner Detection
        line_type = raw_data.get("type")
        is_voip = raw_data.get("is_voip") or False

        if line_type and str(line_type).strip():
            lt_lower = str(line_type).lower()
            if "voip" in lt_lower or "virtual" in lt_lower or is_voip:
                # High-severity warning for VoIP / Virtual Burner numbers
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value="VoIP / VIRTUAL BURNER NUMBER",
                        confidence=0.95,
                        metadata={
                            "field": "voip_detected",
                            "is_voip": True,
                            "line_type": line_type,
                            "risk_level": "HIGH",
                            "data_label": "VoIP / Burner Line",
                            "note": "Virtual Voice-over-IP line (Google Voice, Twilio, TextNow). Commonly used for disposable burner profiles.",
                        },
                    )
                )
            elif "mobile" in lt_lower:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value="Mobile (Cellular)",
                        confidence=0.90,
                        metadata={
                            "field": "line_type",
                            "line_type": "Mobile",
                            "data_label": "Line Type Classification",
                        },
                    )
                )
            elif "landline" in lt_lower or "fixed" in lt_lower:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value="Landline (Fixed Wireline)",
                        confidence=0.90,
                        metadata={
                            "field": "line_type",
                            "line_type": "Landline",
                            "data_label": "Line Type Classification",
                        },
                    )
                )
            else:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value=str(line_type).capitalize(),
                        confidence=0.85,
                        metadata={
                            "field": "line_type",
                            "line_type": line_type,
                        },
                    )
                )

        # Disposable & Risk Facts
        is_disposable = raw_data.get("is_disposable")
        risk_level = raw_data.get("risk_level")

        if is_disposable:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value="DISPOSABLE / BURNER NUMBER",
                    confidence=0.95,
                    metadata={
                        "field": "disposable_detected",
                        "is_disposable": True,
                        "risk_level": "HIGH",
                        "data_label": "Disposable Number Flag",
                    },
                )
            )

        if risk_level and isinstance(risk_level, str) and risk_level.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value=f"RISK LEVEL: {risk_level.upper()}",
                    confidence=0.85,
                    metadata={
                        "field": "phone_risk_level",
                        "risk_level": risk_level.upper(),
                        "data_label": "Phone Risk Rating",
                    },
                )
            )


        # 3. Telecom Carrier Identification
        carrier = raw_data.get("carrier")
        if carrier and isinstance(carrier, str) and carrier.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.ORGANIZATION,
                    value=carrier.strip(),
                    confidence=0.90,
                    metadata={
                        "field": "telecom_carrier",
                        "carrier": carrier.strip(),
                        "data_label": "Telecom Carrier",
                        "note": "Network operator servicing the phone number.",
                    },
                )
            )

        # 4. Geographic Origin & Location
        location = raw_data.get("location")
        country = raw_data.get("country_name")
        country_code = raw_data.get("country_code")

        loc_parts = [p for p in [location, country] if p and isinstance(p, str) and p.strip()]
        if loc_parts:
            loc_val = ", ".join(loc_parts)
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.LOCATION,
                    value=loc_val,
                    confidence=0.80,
                    metadata={
                        "field": "phone_location",
                        "location": location,
                        "country": country,
                        "country_code": country_code,
                        "data_label": "Phone Geographic Origin",
                    },
                )
            )

        return facts
