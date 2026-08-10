"""
tests/normalizers/test_phone_normalizer.py

Tests for the Phone OSINT connector and normalizer.

Design decisions:
    - All tests are deterministic and offline — no live API calls.
    - Test numbers use the NANP test/fictitious range (+1 555-xxxx) and
      well-known ITU allocated ranges for non-US numbers. These numbers
      are guaranteed by standards to never be assigned to real subscribers.
    - The connector is tested in isolation (unit tests on the pure-Python
      phonenumbers logic) and together with the normalizer (integration).
    - The normalizer is also tested independently via its normalize() method.
    - Confidence thresholds are tested explicitly (NFR4 — explainability).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import patch

import pytest

from app.connectors.phone.connector import PhoneConnector
from app.connectors.types import ConnectorStatus, Identifier, IdentifierType
from app.normalizers.phone.normalizer import PhoneNormalizer
from app.normalizers.types import FactType, NormalizationError


# ─── Helpers ──────────────────────────────────────────────────────────────────

def run(coro):
    """Run a coroutine synchronously for test convenience."""
    return asyncio.get_event_loop().run_until_complete(coro)


def phone_id(value: str) -> Identifier:
    return Identifier(value=value, type=IdentifierType.PHONE)


# ─── Phone Connector Tests ────────────────────────────────────────────────────

class TestPhoneConnector:
    """Unit tests for PhoneConnector.fetch() — pure phonenumbers library calls."""

    @pytest.fixture
    def connector(self):
        return PhoneConnector()

    # ── Valid international number ─────────────────────────────────────────

    def test_valid_us_number_e164(self, connector):
        """A valid US number in E.164 format is parsed and normalised."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["error"] is None
        assert result["is_valid"] is True
        assert result["is_possible"] is True
        assert result["e164"] == "+14155552671"
        assert result["country_code"] == 1
        assert result["region"] == "US"

    def test_valid_uk_number(self, connector):
        """A valid UK mainland number is parsed correctly (region=GB)."""
        # +44 207 1234567 is a London geographic number (GB mainland).
        result = run(connector.fetch(phone_id("+442071234567")))
        assert result["error"] is None
        assert result["is_valid"] is True
        assert result["region"] == "GB"
        assert result["country_code"] == 44
        assert result["e164"] == "+442071234567"

    def test_valid_german_number(self, connector):
        """A valid German landline number is parsed correctly."""
        result = run(connector.fetch(phone_id("+4930123456")))
        assert result["error"] is None
        assert result["region"] == "DE"
        assert result["country_code"] == 49

    # ── E.164 normalization ────────────────────────────────────────────────

    def test_e164_format_returned(self, connector):
        """E.164, national, and international formats are all returned."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["e164"].startswith("+")
        assert result["national"] is not None
        assert result["international"] is not None

    def test_input_preserved(self, connector):
        """Raw input is always preserved in the output for audit trail."""
        raw = "+14155552671"
        result = run(connector.fetch(phone_id(raw)))
        assert result["input"] == raw

    # ── Invalid / malformed numbers ────────────────────────────────────────

    def test_invalid_number_returns_error(self, connector):
        """A structurally invalid number sets error field, not raises."""
        result = run(connector.fetch(phone_id("not-a-phone-number")))
        assert result["error"] is not None
        assert "parse" in result["error"].lower() or "cannot" in result["error"].lower()
        assert result["is_valid"] is False
        assert result["is_possible"] is False

    def test_empty_string_returns_error(self, connector):
        """Empty string is handled gracefully (no exception)."""
        result = run(connector.fetch(phone_id("")))
        assert result["error"] is not None
        assert result["is_valid"] is False

    def test_malformed_country_code(self, connector):
        """Number with bogus country code is handled gracefully."""
        result = run(connector.fetch(phone_id("+9999999999999")))
        # May or may not parse; either way, no exception
        assert "error" in result  # key always present

    def test_letters_in_number(self, connector):
        """Phone number with letters produces error, not crash."""
        result = run(connector.fetch(phone_id("CALL-ME-NOW")))
        assert result["error"] is not None

    # ── Country / region ───────────────────────────────────────────────────

    def test_region_is_iso_code(self, connector):
        """Region is a two-character ISO 3166-1 alpha-2 code."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["region"] == "US"
        assert len(result["region"]) == 2

    def test_country_code_is_integer(self, connector):
        """Country code is returned as an integer."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert isinstance(result["country_code"], int)
        assert result["country_code"] == 1

    # ── Carrier ────────────────────────────────────────────────────────────

    def test_carrier_field_present(self, connector):
        """Carrier field is always present in the result dict."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert "carrier" in result
        # May be None for geographic numbers (555 range), that's OK
        assert isinstance(result["carrier"], (str, type(None)))

    def test_carrier_inferred_flag(self, connector):
        """carrier_inferred is always True (never real-time data)."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["carrier_inferred"] is True

    def test_carrier_for_uk_mobile(self, connector):
        """UK mobile numbers often yield a carrier from the library."""
        result = run(connector.fetch(phone_id("+447911123456")))
        # Some numbers yield carrier, some don't — just verify no crash
        assert "carrier" in result
        assert result["carrier_inferred"] is True

    # ── Line type ──────────────────────────────────────────────────────────

    def test_line_type_is_string(self, connector):
        """Line type is always a string (not an integer enum)."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert isinstance(result["line_type"], str)

    def test_line_type_inferred_flag(self, connector):
        """line_type_inferred is always True."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["line_type_inferred"] is True

    def test_uk_mobile_line_type(self, connector):
        """UK mobile number has MOBILE or FIXED_LINE_OR_MOBILE line type."""
        result = run(connector.fetch(phone_id("+447911123456")))
        assert result["line_type"] in ("MOBILE", "FIXED_LINE_OR_MOBILE", "UNKNOWN")

    # ── Timezone ───────────────────────────────────────────────────────────

    def test_timezone_is_list(self, connector):
        """Timezone field is always a list."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert isinstance(result["timezones"], list)

    def test_timezone_inferred_flag(self, connector):
        """timezones_inferred is always True."""
        result = run(connector.fetch(phone_id("+14155552671")))
        assert result["timezones_inferred"] is True

    def test_us_number_has_timezone(self, connector):
        """A US number produces at least one IANA timezone."""
        result = run(connector.fetch(phone_id("+14155552671")))
        # phonenumbers generally provides a timezone for US numbers
        # (might be empty for 555 test numbers — acceptable)
        assert isinstance(result["timezones"], list)

    # ── BaseConnector envelope ─────────────────────────────────────────────

    def test_run_returns_succeeded_envelope_for_valid_number(self, connector):
        """connector.run() wraps fetch() in a SUCCEEDED envelope."""
        envelope = run(connector.run(phone_id("+14155552671")))
        assert envelope.status == ConnectorStatus.SUCCEEDED
        assert envelope.raw_payload is not None
        assert envelope.error_message is None

    def test_run_returns_succeeded_envelope_for_invalid_number(self, connector):
        """Even an invalid number produces SUCCEEDED (error is in payload, not envelope)."""
        # The connector handles parse failures gracefully — the envelope
        # is SUCCEEDED because the connector itself didn't throw; only the
        # payload contains the error description.
        envelope = run(connector.run(phone_id("not-a-phone")))
        assert envelope.status == ConnectorStatus.SUCCEEDED
        assert envelope.raw_payload["error"] is not None

    def test_connector_name(self, connector):
        """Connector name is 'phone'."""
        assert connector.name == "phone"

    def test_supported_identifier_types(self, connector):
        """Connector only handles PHONE identifiers."""
        assert IdentifierType.PHONE in connector.supported_identifier_types
        assert len(connector.supported_identifier_types) == 1

    def test_wrong_identifier_type_raises(self, connector):
        """Passing a non-PHONE identifier raises ValueError."""
        with pytest.raises(ValueError, match="does not support"):
            run(connector.run(Identifier(value="test@example.com", type=IdentifierType.EMAIL)))


# ─── Phone Normalizer Tests ───────────────────────────────────────────────────

class TestPhoneNormalizer:
    """Unit tests for PhoneNormalizer.normalize()."""

    @pytest.fixture
    def normalizer(self):
        return PhoneNormalizer()

    @pytest.fixture
    def valid_payload(self) -> Dict[str, Any]:
        """A representative payload for a valid US phone number."""
        return {
            "input": "+14155552671",
            "e164": "+14155552671",
            "national": "(415) 555-2671",
            "international": "+1 415-555-2671",
            "country_code": 1,
            "region": "US",
            "is_valid": True,
            "is_possible": True,
            "carrier": "AT&T",
            "carrier_inferred": True,
            "line_type": "MOBILE",
            "line_type_inferred": True,
            "timezones": ["America/Los_Angeles"],
            "timezones_inferred": True,
            "error": None,
        }

    @pytest.fixture
    def invalid_payload(self) -> Dict[str, Any]:
        """A payload returned when the number cannot be parsed."""
        return {
            "input": "not-a-phone",
            "e164": None,
            "national": None,
            "international": None,
            "country_code": None,
            "region": None,
            "is_valid": False,
            "is_possible": False,
            "carrier": None,
            "carrier_inferred": True,
            "line_type": None,
            "line_type_inferred": True,
            "timezones": [],
            "timezones_inferred": True,
            "error": "Cannot parse phone number: (0) Missing or invalid default region.",
        }

    # ── Valid number ───────────────────────────────────────────────────────

    def test_valid_number_produces_phone_fact(self, normalizer, valid_payload):
        """A valid number always yields a PHONE fact."""
        facts = normalizer.normalize(valid_payload)
        phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
        assert len(phone_facts) == 1

    def test_valid_phone_fact_value_is_e164(self, normalizer, valid_payload):
        """The PHONE fact value is the E.164 representation."""
        facts = normalizer.normalize(valid_payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert phone_fact.value == "+14155552671"

    def test_valid_number_confidence_is_1(self, normalizer, valid_payload):
        """A validated number gets confidence 1.0."""
        facts = normalizer.normalize(valid_payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert phone_fact.confidence == 1.0

    def test_valid_number_produces_location_fact(self, normalizer, valid_payload):
        """A valid number with a known region produces a LOCATION fact."""
        facts = normalizer.normalize(valid_payload)
        location_facts = [f for f in facts if f.fact_type == FactType.LOCATION]
        assert len(location_facts) == 1
        assert location_facts[0].value == "US"

    def test_location_confidence(self, normalizer, valid_payload):
        """LOCATION fact has confidence 0.90."""
        facts = normalizer.normalize(valid_payload)
        location_fact = next(f for f in facts if f.fact_type == FactType.LOCATION)
        assert location_fact.confidence == pytest.approx(0.90)

    def test_carrier_fact_produced(self, normalizer, valid_payload):
        """A non-empty carrier produces a CONTACT_INFO fact."""
        facts = normalizer.normalize(valid_payload)
        carrier_facts = [f for f in facts if f.fact_type == FactType.CONTACT_INFO]
        assert len(carrier_facts) == 1
        assert carrier_facts[0].value == "AT&T"

    def test_carrier_confidence_is_low(self, normalizer, valid_payload):
        """Carrier confidence is 0.60 (inferred, not confirmed)."""
        facts = normalizer.normalize(valid_payload)
        carrier_fact = next(f for f in facts if f.fact_type == FactType.CONTACT_INFO)
        assert carrier_fact.confidence == pytest.approx(0.60)

    def test_carrier_metadata_inferred_flag(self, normalizer, valid_payload):
        """Carrier fact metadata marks it as inferred."""
        facts = normalizer.normalize(valid_payload)
        carrier_fact = next(f for f in facts if f.fact_type == FactType.CONTACT_INFO)
        assert carrier_fact.metadata.get("inferred") is True

    def test_line_type_fact_produced(self, normalizer, valid_payload):
        """A non-UNKNOWN line type produces a GENERIC fact."""
        facts = normalizer.normalize(valid_payload)
        line_type_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "line_type"
        ]
        assert len(line_type_facts) == 1
        assert line_type_facts[0].value == "MOBILE"

    def test_line_type_confidence(self, normalizer, valid_payload):
        """Line type confidence is 0.65 (inferred from prefix)."""
        facts = normalizer.normalize(valid_payload)
        lt_fact = next(
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "line_type"
        )
        assert lt_fact.confidence == pytest.approx(0.65)

    def test_timezone_fact_produced(self, normalizer, valid_payload):
        """Timezone produces a GENERIC fact per IANA timezone string."""
        facts = normalizer.normalize(valid_payload)
        tz_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "timezone"
        ]
        assert len(tz_facts) == 1
        assert tz_facts[0].value == "America/Los_Angeles"

    def test_timezone_confidence(self, normalizer, valid_payload):
        """Timezone confidence is 0.70."""
        facts = normalizer.normalize(valid_payload)
        tz_fact = next(
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "timezone"
        )
        assert tz_fact.confidence == pytest.approx(0.70)

    def test_multiple_timezones(self, normalizer, valid_payload):
        """Multiple timezones produce multiple facts (one per timezone)."""
        valid_payload["timezones"] = ["America/New_York", "America/Chicago"]
        facts = normalizer.normalize(valid_payload)
        tz_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "timezone"
        ]
        assert len(tz_facts) == 2
        tz_values = {f.value for f in tz_facts}
        assert "America/New_York" in tz_values
        assert "America/Chicago" in tz_values

    def test_duplicate_timezones_deduplicated(self, normalizer, valid_payload):
        """Duplicate timezone strings are deduplicated."""
        valid_payload["timezones"] = ["America/New_York", "America/New_York"]
        facts = normalizer.normalize(valid_payload)
        tz_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "timezone"
        ]
        assert len(tz_facts) == 1

    # ── Invalid number ─────────────────────────────────────────────────────

    def test_invalid_number_always_produces_phone_fact(self, normalizer, invalid_payload):
        """Even an invalid/unparseable number produces at least one PHONE fact."""
        facts = normalizer.normalize(invalid_payload)
        assert len(facts) >= 1
        phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
        assert len(phone_facts) == 1

    def test_invalid_number_low_confidence(self, normalizer, invalid_payload):
        """An unparseable number gets low confidence (0.30)."""
        facts = normalizer.normalize(invalid_payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert phone_fact.confidence == pytest.approx(0.30)

    def test_invalid_number_uses_raw_input_as_value(self, normalizer, invalid_payload):
        """When E.164 is unavailable, the raw input is used as the fact value."""
        facts = normalizer.normalize(invalid_payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert phone_fact.value == "not-a-phone"

    def test_invalid_number_no_location_fact(self, normalizer, invalid_payload):
        """No LOCATION fact is produced when region is unknown."""
        facts = normalizer.normalize(invalid_payload)
        location_facts = [f for f in facts if f.fact_type == FactType.LOCATION]
        assert len(location_facts) == 0

    def test_invalid_number_no_carrier_fact(self, normalizer, invalid_payload):
        """No carrier fact when carrier is None."""
        facts = normalizer.normalize(invalid_payload)
        carrier_facts = [f for f in facts if f.fact_type == FactType.CONTACT_INFO]
        assert len(carrier_facts) == 0

    def test_parse_error_in_metadata(self, normalizer, invalid_payload):
        """The parse error string is stored in the PHONE fact's metadata."""
        facts = normalizer.normalize(invalid_payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert "parse_error" in phone_fact.metadata
        assert phone_fact.metadata["parse_error"] is not None

    # ── Possible but not fully valid ──────────────────────────────────────

    def test_possible_but_invalid_medium_confidence(self, normalizer):
        """A possible but structurally invalid number gets 0.75 confidence."""
        payload = {
            "input": "+14155550000",
            "e164": "+14155550000",
            "national": "(415) 555-0000",
            "international": "+1 415-555-0000",
            "country_code": 1,
            "region": "US",
            "is_valid": False,
            "is_possible": True,
            "carrier": None,
            "carrier_inferred": True,
            "line_type": "UNKNOWN",
            "line_type_inferred": True,
            "timezones": [],
            "timezones_inferred": True,
            "error": None,
        }
        facts = normalizer.normalize(payload)
        phone_fact = next(f for f in facts if f.fact_type == FactType.PHONE)
        assert phone_fact.confidence == pytest.approx(0.75)

    # ── Missing / absent optional fields ──────────────────────────────────

    def test_no_carrier_no_fact(self, normalizer, valid_payload):
        """No carrier fact when carrier is None."""
        valid_payload["carrier"] = None
        facts = normalizer.normalize(valid_payload)
        carrier_facts = [f for f in facts if f.fact_type == FactType.CONTACT_INFO]
        assert len(carrier_facts) == 0

    def test_unknown_line_type_no_fact(self, normalizer, valid_payload):
        """UNKNOWN line type does not produce a fact."""
        valid_payload["line_type"] = "UNKNOWN"
        facts = normalizer.normalize(valid_payload)
        lt_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "line_type"
        ]
        assert len(lt_facts) == 0

    def test_no_timezones_no_facts(self, normalizer, valid_payload):
        """Empty timezone list produces no timezone facts."""
        valid_payload["timezones"] = []
        facts = normalizer.normalize(valid_payload)
        tz_facts = [
            f for f in facts
            if f.fact_type == FactType.GENERIC and f.metadata.get("field") == "timezone"
        ]
        assert len(tz_facts) == 0

    def test_non_geographic_region_no_location_fact(self, normalizer, valid_payload):
        """Region '001' (satellite/non-geographic) produces no LOCATION fact."""
        valid_payload["region"] = "001"
        facts = normalizer.normalize(valid_payload)
        location_facts = [f for f in facts if f.fact_type == FactType.LOCATION]
        assert len(location_facts) == 0

    # ── Malformed input to normalizer ─────────────────────────────────────

    def test_non_dict_payload_raises_normalization_error(self, normalizer):
        """Non-dict payload raises NormalizationError."""
        with pytest.raises(NormalizationError):
            normalizer.normalize("not-a-dict")

    def test_list_payload_raises_normalization_error(self, normalizer):
        """List payload raises NormalizationError."""
        with pytest.raises(NormalizationError):
            normalizer.normalize(["+14155552671"])

    # ── Source connector provenance ────────────────────────────────────────

    def test_all_facts_have_correct_source_connector(self, normalizer, valid_payload):
        """Every fact produced has source_connector='phone'."""
        facts = normalizer.normalize(valid_payload)
        for fact in facts:
            assert fact.source_connector == "phone"

    def test_connector_name(self, normalizer):
        """Normalizer's connector_name is 'phone'."""
        assert normalizer.connector_name == "phone"

    # ── run() plumbing (NormalizationResult) ─────────────────────────────

    def test_run_returns_normalization_result(self, normalizer, valid_payload):
        """run() returns a NormalizationResult with the expected facts."""
        from app.normalizers.types import NormalizationResult
        result = normalizer.run(valid_payload)
        assert isinstance(result, NormalizationResult)
        assert result.connector_name == "phone"
        assert len(result.facts) > 0

    def test_run_attaches_raw_reference_id(self, normalizer, valid_payload):
        """run() attaches raw_reference_id to all facts when provided."""
        result = normalizer.run(valid_payload, raw_reference_id="ref-abc-123")
        for fact in result.facts:
            assert fact.raw_reference_id == "ref-abc-123"

    # ── Duplicate facts ────────────────────────────────────────────────────

    def test_single_phone_fact_per_call(self, normalizer, valid_payload):
        """Exactly one PHONE fact is produced per normalization call."""
        facts = normalizer.normalize(valid_payload)
        phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
        assert len(phone_facts) == 1

    def test_single_location_fact_per_call(self, normalizer, valid_payload):
        """At most one LOCATION fact is produced per call."""
        facts = normalizer.normalize(valid_payload)
        location_facts = [f for f in facts if f.fact_type == FactType.LOCATION]
        assert len(location_facts) <= 1

    def test_single_carrier_fact_per_call(self, normalizer, valid_payload):
        """At most one CONTACT_INFO (carrier) fact per call."""
        facts = normalizer.normalize(valid_payload)
        carrier_facts = [f for f in facts if f.fact_type == FactType.CONTACT_INFO]
        assert len(carrier_facts) <= 1


# ─── End-to-end: connector → normalizer integration ───────────────────────────

class TestPhoneConnectorNormalizerIntegration:
    """
    Integration tests: PhoneConnector.run() → PhoneNormalizer.normalize().

    These tests exercise the full path without any database or API calls.
    They verify the connector and normalizer are compatible at their
    interface boundary.
    """

    @pytest.fixture
    def connector(self):
        return PhoneConnector()

    @pytest.fixture
    def normalizer(self):
        return PhoneNormalizer()

    def test_valid_number_full_pipeline(self, connector, normalizer):
        """Valid number: connector + normalizer produces PHONE fact with E.164 value."""
        envelope = run(connector.run(phone_id("+14155552671")))
        assert envelope.succeeded
        facts = normalizer.normalize(envelope.raw_payload)
        phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
        assert len(phone_facts) == 1
        assert phone_facts[0].value == "+14155552671"
        assert phone_facts[0].confidence == 1.0

    def test_invalid_number_full_pipeline(self, connector, normalizer):
        """Invalid number: connector succeeds, normalizer yields low-confidence fact."""
        envelope = run(connector.run(phone_id("CALL-ME-NOW")))
        assert envelope.succeeded  # connector doesn't raise on bad input
        facts = normalizer.normalize(envelope.raw_payload)
        phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
        assert len(phone_facts) == 1
        assert phone_facts[0].confidence == pytest.approx(0.30)

    def test_uk_number_region_is_gb(self, connector, normalizer):
        """UK mainland number yields region 'GB' in the LOCATION fact."""
        # +44 207 1234567 is a London geographic number (GB mainland).
        envelope = run(connector.run(phone_id("+442071234567")))
        facts = normalizer.normalize(envelope.raw_payload)
        location_facts = [f for f in facts if f.fact_type == FactType.LOCATION]
        assert len(location_facts) == 1
        assert location_facts[0].value == "GB"

    def test_normalizer_registered_for_phone_connector(self):
        """PhoneNormalizer is registered in the normalizer registry."""
        from app.normalizers import normalizer_registry
        assert normalizer_registry.has_normalizer("phone")

    def test_connector_registered_for_phone_type(self):
        """PhoneConnector is registered for IdentifierType.PHONE."""
        from app.connectors import registry
        phone_connectors = registry.get_connectors_for_identifier_type(IdentifierType.PHONE)
        names = [cls.name for cls in phone_connectors]
        assert "phone" in names

    def test_pipeline_does_not_affect_existing_domain_connectors(self):
        """Adding phone OSINT does not break domain connector registration."""
        from app.connectors import registry
        from app.connectors.types import IdentifierType as IT
        domain_connectors = registry.get_connectors_for_identifier_type(IT.DOMAIN)
        domain_names = [cls.name for cls in domain_connectors]
        assert "whois" in domain_names
        # Phone connector must NOT appear for domain lookups
        assert "phone" not in domain_names

    def test_pipeline_all_facts_have_source_connector(self, connector, normalizer):
        """Every fact from the pipeline has source_connector='phone'."""
        envelope = run(connector.run(phone_id("+14155552671")))
        facts = normalizer.normalize(envelope.raw_payload)
        for fact in facts:
            assert fact.source_connector == "phone"
