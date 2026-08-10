"""
connectors/phone/connector.py

Phone OSINT connector using the `phonenumbers` library.

This connector:
    1. Subclasses BaseConnector and registers via @registry.register.
    2. Accepts only PHONE identifiers.
    3. Uses phonenumbers (pure-Python, offline, zero external APIs) to
       parse, validate, and extract publicly-available metadata about
       a phone number.
    4. Returns a raw JSON-serializable dictionary for downstream
       normalization (M3). It performs NO normalization itself.
    5. Does NOT access any database, paid API, breach database, or
       any real-time location/enumeration service.

IMPORTANT — Responsible-use boundary (MASTER_DESIGN.md §4.3):
    Carrier and line-type data is statically inferred from the number
    prefix by the phonenumbers library. It is NOT confirmed real-time
    carrier data and MUST NOT be presented as confirmed ownership
    information about a specific person. The normalizer (M3) assigns
    appropriately reduced confidence to these inferred facts.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, FrozenSet

import phonenumbers
from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    PhoneNumberType,
    geocoder,
    carrier as carrier_module,
    timezone as timezone_module,
)

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType

# Map phonenumbers PhoneNumberType integer constants to readable strings.
# phonenumbers returns an int enum; we convert to a stable string so the
# normalizer and downstream code never need to import phonenumbers directly.
_LINE_TYPE_NAMES: Dict[int, str] = {
    PhoneNumberType.FIXED_LINE: "FIXED_LINE",
    PhoneNumberType.MOBILE: "MOBILE",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
    PhoneNumberType.TOLL_FREE: "TOLL_FREE",
    PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
    PhoneNumberType.SHARED_COST: "SHARED_COST",
    PhoneNumberType.VOIP: "VOIP",
    PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
    PhoneNumberType.PAGER: "PAGER",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "VOICEMAIL",
    PhoneNumberType.UNKNOWN: "UNKNOWN",
}


@registry.register
class PhoneConnector(BaseConnector):
    """
    Phone OSINT connector — parses and analyses phone numbers using the
    phonenumbers library (offline, no external API calls).

    Produces a structured dict containing:
        - Normalized E.164 form and alternative display formats.
        - Country code and region.
        - Valid/possible flags (library's own assessment).
        - Carrier name (inferred from prefix — not real-time).
        - Line type (mobile/landline/VoIP/etc. — inferred from prefix).
        - Timezone(s) associated with the number's area.
        - Error string if the input cannot be parsed.

    All inferred metadata (carrier, line type, timezone) is labelled in
    the raw payload so the normalizer can assign lower confidence scores
    to inferred vs. structurally-derived facts.
    """

    name: ClassVar[str] = "phone"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.PHONE}
    )
    # phonenumbers is pure-Python/offline — very fast; a tight timeout is safe.
    timeout_seconds: ClassVar[float] = 5.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Parse and analyse a phone number using the phonenumbers library.

        Args:
            identifier: A PHONE identifier whose value is an international
                or national phone number string (e.g., "+14155552671" or
                "415-555-2671" with a default_region hint).

        Returns:
            A JSON-serializable dict with all extracted facts and an
            `error` field (None on success, error string on failure).
            The envelope is always returned (never raises) — the
            BaseConnector.run() wrapper handles unexpected exceptions,
            but phonenumbers parse failures are handled gracefully here
            so the investigation pipeline gets useful partial data.
        """
        raw_value = identifier.value.strip()
        result: Dict[str, Any] = {
            "input": raw_value,
            "e164": None,
            "national": None,
            "international": None,
            "country_code": None,
            "region": None,
            "is_valid": False,
            "is_possible": False,
            "carrier": None,
            "carrier_inferred": True,   # always inferred from prefix, never real-time
            "line_type": None,
            "line_type_inferred": True,  # always inferred from prefix
            "timezones": [],
            "timezones_inferred": True,  # derived from area code, not real-time
            "error": None,
        }

        # ── Parse ──────────────────────────────────────────────────────────
        try:
            # Try parsing as an international number first (E.164 / +CC format).
            # If that fails, fall back with no default region (will produce an
            # informative error rather than silently guessing a wrong region).
            parsed = phonenumbers.parse(raw_value, None)
        except NumberParseException as exc:
            result["error"] = f"Cannot parse phone number: {exc}"
            return result

        # ── Validate ───────────────────────────────────────────────────────
        is_possible = phonenumbers.is_possible_number(parsed)
        is_valid = phonenumbers.is_valid_number(parsed)
        result["is_possible"] = is_possible
        result["is_valid"] = is_valid

        # ── Formatted representations ──────────────────────────────────────
        result["e164"] = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        result["national"] = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
        result["international"] = phonenumbers.format_number(
            parsed, PhoneNumberFormat.INTERNATIONAL
        )
        result["country_code"] = parsed.country_code

        # ── Region (ISO 3166-1 alpha-2) ────────────────────────────────────
        region = phonenumbers.region_code_for_number(parsed)
        result["region"] = region  # may be "001" for international (non-geographic)

        # ── Carrier (inferred from prefix — not real-time) ─────────────────
        # Only attempt for valid/possible numbers; returns "" for unknowns.
        if is_possible or is_valid:
            carrier_name = carrier_module.name_for_number(parsed, "en")
            result["carrier"] = carrier_name if carrier_name else None

        # ── Line type (inferred from prefix — not real-time) ──────────────
        line_type_int = phonenumbers.number_type(parsed)
        result["line_type"] = _LINE_TYPE_NAMES.get(line_type_int, "UNKNOWN")

        # ── Timezones (derived from area code, not GPS/real-time) ─────────
        tzs = list(timezone_module.time_zones_for_number(parsed))
        result["timezones"] = tzs  # list of IANA timezone strings, may be empty

        return result
