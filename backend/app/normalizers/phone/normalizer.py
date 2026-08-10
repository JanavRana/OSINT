"""
normalizers/phone/normalizer.py

Phone OSINT normalizer — converts the PhoneConnector's raw dict into
normalized facts following the shared internal schema (M3, Section 11.3
of MASTER_DESIGN.md).

Confidence assignments (MASTER_DESIGN.md §4.3 / NFR4 — explainability):

    PHONE (E.164 value, structurally valid)     → 1.00
    PHONE (possible but structurally invalid)   → 0.75
    LOCATION (country/region from number prefix)→ 0.90
    CONTACT_INFO (carrier — inferred, not real) → 0.60
    GENERIC (line type — inferred from prefix)  → 0.65
    GENERIC (timezone — derived from area code) → 0.70

IMPORTANT: Carrier and line-type data is prefix-inferred, NOT confirmed
real-time data. These facts MUST NOT be interpreted as confirmed identity
or ownership information about a specific person. The reduced confidence
scores (0.60, 0.65) communicate this uncertainty to downstream consumers.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class PhoneNormalizer(BaseNormalizer):
    """
    Normalizer for the 'phone' connector's raw payload.

    Extracts one or more NormalizedFact instances from the structured
    dict produced by PhoneConnector.fetch():

        - PHONE fact:       the E.164-normalized number (or best-effort
                            international form) with validity flags.
        - LOCATION fact:    country/region derived from the country code.
        - CONTACT_INFO fact: carrier name (inferred, lower confidence).
        - GENERIC facts:    line type and timezone(s) (both inferred).

    If the connector reported a parse error, one PHONE fact is still
    produced (using the raw input value) with low confidence so the
    investigation pipeline has a record of the attempt.
    """

    connector_name: ClassVar[str] = "phone"

    # ── Confidence constants ───────────────────────────────────────────────
    # Named constants make the reasoning visible and easy to adjust.
    _CONF_E164_VALID: float = 1.00       # structurally valid E.164 number
    _CONF_E164_POSSIBLE: float = 0.75    # possible but not fully validated
    _CONF_E164_PARSE_FAIL: float = 0.30  # raw input, could not be parsed
    _CONF_REGION: float = 0.90           # country/region from number prefix
    _CONF_CARRIER: float = 0.60          # inferred carrier — not real-time
    _CONF_LINE_TYPE: float = 0.65        # inferred line type from prefix
    _CONF_TIMEZONE: float = 0.70         # area-code-derived timezone

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert PhoneConnector's raw dict into normalized facts.

        Args:
            raw_payload: The dict returned by PhoneConnector.fetch().

        Returns:
            A list of NormalizedFact instances. Never empty — always at
            least one PHONE fact (even on parse failure, to preserve the
            audit trail of the attempt).

        Raises:
            NormalizationError: If raw_payload is not a dict at all
                (genuinely malformed input, distinct from a parse-failure
                reported inside a well-formed dict).
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )

        facts: List[NormalizedFact] = []

        error = raw_payload.get("error")
        is_valid = raw_payload.get("is_valid", False)
        is_possible = raw_payload.get("is_possible", False)

        # ── 1. Primary PHONE fact ──────────────────────────────────────────
        phone_fact = self._build_phone_fact(raw_payload, is_valid, is_possible, error)
        facts.append(phone_fact)

        # Stop here if the number could not be parsed at all — the
        # remaining fields are unreliable without a parsed number.
        if error and not is_possible:
            return facts

        # ── 2. LOCATION — country/region ──────────────────────────────────
        location_fact = self._build_location_fact(raw_payload)
        if location_fact:
            facts.append(location_fact)

        # ── 3. CONTACT_INFO — carrier (inferred, not real-time) ───────────
        carrier_fact = self._build_carrier_fact(raw_payload)
        if carrier_fact:
            facts.append(carrier_fact)

        # ── 4. GENERIC — line type (inferred from prefix) ─────────────────
        line_type_fact = self._build_line_type_fact(raw_payload)
        if line_type_fact:
            facts.append(line_type_fact)

        # ── 5. GENERIC — timezone(s) (area-code-derived) ──────────────────
        timezone_facts = self._build_timezone_facts(raw_payload)
        facts.extend(timezone_facts)

        return facts

    # ── Private builders ──────────────────────────────────────────────────

    def _build_phone_fact(
        self,
        payload: Dict[str, Any],
        is_valid: bool,
        is_possible: bool,
        error: Optional[str],
    ) -> NormalizedFact:
        """Build the primary PHONE fact."""
        # Prefer E.164 → international → raw input (in that order)
        e164 = payload.get("e164")
        intl = payload.get("international")
        raw = payload.get("input", "")
        value = e164 or intl or raw

        if is_valid:
            confidence = self._CONF_E164_VALID
        elif is_possible:
            confidence = self._CONF_E164_POSSIBLE
        else:
            confidence = self._CONF_E164_PARSE_FAIL

        metadata: Dict[str, Any] = {
            "field": "phone_number",
            "is_valid": is_valid,
            "is_possible": is_possible,
            "e164": e164,
            "national": payload.get("national"),
            "international": intl,
            "country_code": payload.get("country_code"),
        }
        if error:
            metadata["parse_error"] = error

        return NormalizedFact(
            fact_type=FactType.PHONE,
            value=value,
            source_connector=self.connector_name,
            confidence=confidence,
            metadata=metadata,
        )

    def _build_location_fact(self, payload: Dict[str, Any]) -> Optional[NormalizedFact]:
        """Build a LOCATION fact from the number's region/state."""
        region = payload.get("region")
        country_code = payload.get("country_code")
        state_region = payload.get("state_region")

        if not region and not country_code and not state_region:
            return None
        # "001" is phonenumbers' sentinel for non-geographic numbers (e.g. satellite)
        if region == "001":
            return None

        location_value = state_region or region or str(country_code)
        return NormalizedFact(
            fact_type=FactType.LOCATION,
            value=location_value,
            source_connector=self.connector_name,
            confidence=self._CONF_REGION,
            metadata={
                "field": "region",
                "region": region,
                "state_region": state_region,
                "country_code": country_code,
                "derived_from": "indian_numbering_plan" if country_code == 91 else "number_prefix",
            },
        )

    def _build_carrier_fact(self, payload: Dict[str, Any]) -> Optional[NormalizedFact]:
        """
        Build a CONTACT_INFO fact for the carrier name.

        IMPORTANT: This is a prefix-inferred carrier, not a real-time
        lookup. Confidence is intentionally low (0.60) to reflect that
        this data CANNOT be used to confirm who owns the number.
        """
        carrier = payload.get("carrier")
        if not carrier:
            return None

        return NormalizedFact(
            fact_type=FactType.CONTACT_INFO,
            value=carrier,
            source_connector=self.connector_name,
            confidence=self._CONF_CARRIER,
            metadata={
                "field": "carrier",
                "inferred": True,
                "note": (
                    "Carrier is inferred from the number prefix, not confirmed "
                    "by real-time lookup. Do not use as confirmed ownership data."
                ),
            },
        )

    def _build_line_type_fact(self, payload: Dict[str, Any]) -> Optional[NormalizedFact]:
        """
        Build a GENERIC fact for the line type (MOBILE, FIXED_LINE, etc.).

        Confidence is 0.65 because line type is inferred from the prefix
        by the phonenumbers library — not real-time network data.
        """
        line_type = payload.get("line_type")
        if not line_type or line_type == "UNKNOWN":
            return None

        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=line_type,
            source_connector=self.connector_name,
            confidence=self._CONF_LINE_TYPE,
            metadata={
                "field": "line_type",
                "inferred": True,
            },
        )

    def _build_timezone_facts(
        self, payload: Dict[str, Any]
    ) -> List[NormalizedFact]:
        """
        Build GENERIC facts for timezone(s).

        One fact per IANA timezone string. Confidence is 0.70 because
        timezones are derived from area code / number prefix, not from
        the subscriber's actual location.
        """
        timezones = payload.get("timezones", [])
        if not isinstance(timezones, list):
            return []

        facts = []
        seen: set = set()
        for tz in timezones:
            if not isinstance(tz, str) or not tz or tz in seen:
                continue
            seen.add(tz)
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=tz,
                    source_connector=self.connector_name,
                    confidence=self._CONF_TIMEZONE,
                    metadata={
                        "field": "timezone",
                        "inferred": True,
                    },
                )
            )
        return facts
