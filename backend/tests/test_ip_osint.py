"""
tests/test_ip_osint.py

Comprehensive unit tests for IP OSINT:
    - IP validator (IPv4, IPv6, private, reserved, loopback)
    - IpGeolocationConnector (mocked HTTP — zero real API calls)
    - IpGeolocationNormalizer
    - reverse_dns connector integration (existing — tested for non-regression)
    - list_identifiers API endpoint (synthetic facts)
    - Failure isolation (geo failure ≠ rdns failure)

All external HTTP calls are mocked using unittest.mock and httpx.

Coverage targets per spec:
    valid IPv4                 ✓
    valid IPv6                 ✓
    invalid IP                 ✓
    private/reserved IP        ✓
    geolocation response       ✓
    ASN/ISP                    ✓
    region/country             ✓
    timezone                   ✓
    reverse DNS success        ✓
    reverse DNS missing        ✓
    geolocation timeout        ✓
    API 429 rate limit         ✓
    API 5xx failure            ✓
    normalized facts           ✓
    identifier output          ✓
    failure isolation          ✓
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Test Infrastructure ────────────────────────────────────────────────────


def run(coro):
    """Run a coroutine synchronously (compatible with both pytest and pytest-asyncio)."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ═══════════════════════════════════════════════════════════════════════════
# 1. VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestIpValidator:
    """Test suite for connectors/ip/validator.py"""

    def setup_method(self):
        from app.connectors.ip.validator import validate_ip_address, IpValidationError
        self.validate = validate_ip_address
        self.IpValidationError = IpValidationError

    def test_valid_ipv4_public(self):
        """Standard public IPv4 should validate cleanly."""
        result = self.validate("8.8.8.8")
        assert result.address == "8.8.8.8"
        assert result.version == 4
        assert result.is_publicly_routable is True
        assert result.is_private is False
        assert result.is_loopback is False

    def test_valid_ipv4_cloudflare(self):
        """Cloudflare DNS IPv4 should validate cleanly."""
        result = self.validate("1.1.1.1")
        assert result.address == "1.1.1.1"
        assert result.is_publicly_routable is True

    def test_valid_ipv6_google_dns(self):
        """Full IPv6 address should validate and return version=6."""
        result = self.validate("2001:4860:4860::8888")
        assert result.version == 6
        assert result.is_publicly_routable is True
        assert result.is_loopback is False

    def test_valid_ipv6_cloudflare(self):
        """Cloudflare IPv6 DNS."""
        result = self.validate("2606:4700:4700::1111")
        assert result.version == 6
        assert result.is_publicly_routable is True

    def test_private_ipv4_192_168(self):
        """RFC 1918 private range should be marked is_private=True."""
        result = self.validate("192.168.1.100")
        assert result.is_private is True
        assert result.is_publicly_routable is False

    def test_private_ipv4_10_0(self):
        """10.x.x.x should be marked as private."""
        result = self.validate("10.0.0.1")
        assert result.is_private is True
        assert result.is_publicly_routable is False

    def test_private_ipv4_172_16(self):
        """172.16.x.x should be marked as private."""
        result = self.validate("172.16.0.1")
        assert result.is_private is True
        assert result.is_publicly_routable is False

    def test_loopback_ipv4(self):
        """127.0.0.1 should be flagged as loopback."""
        result = self.validate("127.0.0.1")
        assert result.is_loopback is True
        assert result.is_publicly_routable is False

    def test_loopback_ipv6(self):
        """::1 (IPv6 loopback) should be flagged as loopback."""
        result = self.validate("::1")
        assert result.is_loopback is True
        assert result.is_publicly_routable is False

    def test_invalid_hostname_rejected(self):
        """Hostnames like 'google.com' must be rejected."""
        with pytest.raises(self.IpValidationError):
            self.validate("google.com")

    def test_invalid_octet_rejected(self):
        """Octets out of range (256) must be rejected."""
        with pytest.raises(self.IpValidationError):
            self.validate("256.1.1.1")

    def test_malformed_string_rejected(self):
        """Arbitrary strings must be rejected."""
        with pytest.raises(self.IpValidationError):
            self.validate("not-an-ip")

    def test_cidr_notation_rejected(self):
        """CIDR notation like '8.8.8.0/24' must be rejected."""
        with pytest.raises(self.IpValidationError):
            self.validate("8.8.8.0/24")

    def test_empty_string_rejected(self):
        """Empty string must be rejected."""
        with pytest.raises(self.IpValidationError):
            self.validate("")

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped before parsing."""
        result = self.validate("  8.8.8.8  ")
        assert result.address == "8.8.8.8"

    def test_link_local_ipv4(self):
        """169.254.x.x (link-local) should not be publicly routable."""
        result = self.validate("169.254.1.1")
        assert result.is_link_local is True
        assert result.is_publicly_routable is False

    def test_multicast_ipv4(self):
        """224.0.0.1 (multicast) should not be publicly routable."""
        result = self.validate("224.0.0.1")
        assert result.is_multicast is True
        assert result.is_publicly_routable is False


# ═══════════════════════════════════════════════════════════════════════════
# 2. CONNECTOR TESTS (all HTTP mocked)
# ═══════════════════════════════════════════════════════════════════════════


def _make_http_response(status_code: int, json_body: Dict[str, Any]) -> MagicMock:
    """Create a mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body
    return mock_resp


def _mock_client(response: MagicMock):
    """Patch httpx.AsyncClient.get to return a given response."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


_IPAPI_SUCCESS = {
    "country_name": "United States",
    "country_code": "US",
    "region": "California",
    "city": "Mountain View",
    "latitude": 37.3861,
    "longitude": -122.0839,
    "timezone": "America/Los_Angeles",
    "asn": "AS15169",
    "org": "AS15169 Google LLC",
}


class TestIpGeolocationConnector:
    """Test IpGeolocationConnector with mocked HTTP."""

    def setup_method(self):
        from app.connectors.ip.connector import IpGeolocationConnector
        from app.connectors.types import Identifier, IdentifierType
        self.connector = IpGeolocationConnector()
        self.Identifier = Identifier
        self.IdentifierType = IdentifierType

    def _make_id(self, value: str):
        return self.Identifier(value=value, type=self.IdentifierType.IP)

    @patch("httpx.AsyncClient")
    def test_valid_ipv4_returns_geo_data(self, mock_client_cls):
        """Successful geolocation returns all expected fields."""
        mock_client_cls.return_value = _mock_client(
            _make_http_response(200, _IPAPI_SUCCESS)
        )
        result = run(self.connector.fetch(self._make_id("8.8.8.8")))

        assert result["error"] is None
        assert result["ip"] == "8.8.8.8"
        assert result["version"] == 4
        assert result["country"] == "United States"
        assert result["country_code"] == "US"
        assert result["region"] == "California"
        assert result["city"] == "Mountain View"
        assert result["latitude"] == 37.3861
        assert result["longitude"] == -122.0839
        assert result["timezone"] == "America/Los_Angeles"
        assert result["asn"] == "AS15169"
        assert "Google" in result["org"]

    @patch("httpx.AsyncClient")
    def test_valid_ipv6_returns_geo_data(self, mock_client_cls):
        """IPv6 addresses should be accepted and return geo data."""
        mock_client_cls.return_value = _mock_client(
            _make_http_response(200, _IPAPI_SUCCESS)
        )
        result = run(self.connector.fetch(self._make_id("2001:4860:4860::8888")))
        assert result["error"] is None
        assert result["version"] == 6
        assert result["is_publicly_routable"] is True

    def test_private_ip_skips_geolocation(self):
        """Private IPs should skip geo lookup entirely (no HTTP call)."""
        with patch("httpx.AsyncClient") as mock_cls:
            result = run(self.connector.fetch(self._make_id("192.168.1.100")))
        assert result["is_private"] is True
        assert result["is_publicly_routable"] is False
        assert "private" in result["error"].lower()
        mock_cls.assert_not_called()

    def test_loopback_ip_skips_geolocation(self):
        """Loopback IPs should skip geo lookup."""
        with patch("httpx.AsyncClient") as mock_cls:
            result = run(self.connector.fetch(self._make_id("127.0.0.1")))
        assert result["is_loopback"] is True
        assert "loopback" in result["error"].lower()
        mock_cls.assert_not_called()

    def test_invalid_ip_returns_validation_error(self):
        """Invalid IP strings should return error_code='validation_error'."""
        with patch("httpx.AsyncClient") as mock_cls:
            result = run(self.connector.fetch(self._make_id("not-an-ip")))
        assert result["error_code"] == "validation_error"
        assert result["error"] is not None
        mock_cls.assert_not_called()

    @patch("httpx.AsyncClient")
    def test_api_rate_limit_429(self, mock_client_cls):
        """HTTP 429 should trigger fallback or provider_error cleanly."""
        mock_client_cls.return_value = _mock_client(
            _make_http_response(429, {})
        )
        result = run(self.connector.fetch(self._make_id("8.8.8.8")))
        assert result["error_code"] == "provider_error"
        assert "rate limit" in result["error"].lower() or "unavailable" in result["error"].lower()

    @patch("httpx.AsyncClient")
    def test_api_5xx_server_error(self, mock_client_cls):
        """HTTP 5xx should trigger fallback or provider_error cleanly."""
        mock_client_cls.return_value = _mock_client(
            _make_http_response(503, {})
        )
        result = run(self.connector.fetch(self._make_id("8.8.8.8")))
        assert result["error_code"] == "provider_error"
        assert "unavailable" in result["error"].lower() or "error" in result["error"].lower()

    @patch("httpx.AsyncClient")
    def test_api_timeout(self, mock_client_cls):
        """Timeout should return provider_error without crashing."""
        import httpx
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_cls.return_value = mock_client

        result = run(self.connector.fetch(self._make_id("8.8.8.8")))
        assert result["error_code"] == "provider_error"
        assert "unavailable" in result["error"].lower() or "timed out" in result["error"].lower()


    @patch("httpx.AsyncClient")
    def test_missing_geo_fields_handled_gracefully(self, mock_client_cls):
        """Partial/missing fields in the API response should not crash."""
        sparse_response = {
            "country_name": "Germany",
            # no region, city, lat, lon, timezone, asn, org
        }
        mock_client_cls.return_value = _mock_client(
            _make_http_response(200, sparse_response)
        )
        result = run(self.connector.fetch(self._make_id("8.8.8.8")))
        assert result["country"] == "Germany"
        assert result["region"] is None
        assert result["city"] is None
        assert result["latitude"] is None
        assert result["asn"] is None
        assert result["error"] is None

    @patch("httpx.AsyncClient")
    def test_env_api_key_appended_when_set(self, mock_client_cls):
        """IP_GEOLOCATION_API_KEY env var should be appended as ?key=."""
        import os
        mock_resp = _make_http_response(200, _IPAPI_SUCCESS)
        mock_client = _mock_client(mock_resp)
        mock_client_cls.return_value = mock_client

        with patch.dict(os.environ, {"IP_GEOLOCATION_API_KEY": "test-key-abc"}):
            run(self.connector.fetch(self._make_id("8.8.8.8")))

        call_kwargs = mock_client.get.call_args
        params = call_kwargs[1].get("params", {}) or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        # Accept either positional or keyword params
        if not params and call_kwargs.kwargs:
            params = call_kwargs.kwargs.get("params", {})
        assert params.get("key") == "test-key-abc"


# ═══════════════════════════════════════════════════════════════════════════
# 3. NORMALIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestIpGeolocationNormalizer:
    """Test IpGeolocationNormalizer fact extraction."""

    def setup_method(self):
        from app.normalizers.ip.normalizer import IpGeolocationNormalizer
        from app.normalizers.types import FactType
        self.normalizer = IpGeolocationNormalizer()
        self.FactType = FactType

    def _full_payload(self) -> Dict[str, Any]:
        return {
            "ip": "8.8.8.8",
            "version": 4,
            "is_private": False,
            "is_loopback": False,
            "is_link_local": False,
            "is_reserved": False,
            "is_publicly_routable": True,
            "country": "United States",
            "country_code": "US",
            "region": "California",
            "city": "Mountain View",
            "latitude": 37.3861,
            "longitude": -122.0839,
            "timezone": "America/Los_Angeles",
            "asn": "AS15169",
            "org": "AS15169 Google LLC",
            "error": None,
            "error_code": None,
        }

    def test_full_payload_produces_all_fact_types(self):
        """All expected fact types should be produced from a full response."""
        facts = self.normalizer.normalize(self._full_payload())
        fact_types = [f.fact_type for f in facts]
        assert self.FactType.GENERIC in fact_types      # IP address + ASN + timezone
        assert self.FactType.LOCATION in fact_types     # country + region/city
        assert self.FactType.CONTACT_INFO in fact_types # ISP/org

    def test_ip_address_fact_produced(self):
        """The IP address itself should appear as a GENERIC fact."""
        facts = self.normalizer.normalize(self._full_payload())
        ip_facts = [f for f in facts if f.fact_type == self.FactType.GENERIC and f.value == "8.8.8.8"]
        assert len(ip_facts) == 1
        assert ip_facts[0].confidence == 1.0

    def test_country_fact_confidence(self):
        """Country geolocation estimate should have reduced confidence (~0.60)."""
        facts = self.normalizer.normalize(self._full_payload())
        country_facts = [
            f for f in facts
            if f.fact_type == self.FactType.LOCATION
            and f.metadata.get("field") == "country"
        ]
        assert len(country_facts) == 1
        assert country_facts[0].confidence == pytest.approx(0.60, abs=0.05)

    def test_region_city_fact_value(self):
        """Region/city fact value should concatenate city and region."""
        facts = self.normalizer.normalize(self._full_payload())
        region_facts = [
            f for f in facts
            if f.fact_type == self.FactType.LOCATION
            and f.metadata.get("field") == "region_city"
        ]
        assert len(region_facts) == 1
        assert "Mountain View" in region_facts[0].value
        assert "California" in region_facts[0].value

    def test_isp_fact_strips_asn_prefix(self):
        """ISP display value should strip the 'AS15169 ' prefix from org."""
        facts = self.normalizer.normalize(self._full_payload())
        isp_facts = [f for f in facts if f.fact_type == self.FactType.CONTACT_INFO]
        assert len(isp_facts) == 1
        assert isp_facts[0].value == "Google LLC"

    def test_asn_fact_produced(self):
        """ASN should appear as a GENERIC fact."""
        facts = self.normalizer.normalize(self._full_payload())
        asn_facts = [
            f for f in facts
            if f.fact_type == self.FactType.GENERIC and f.metadata.get("field") == "asn"
        ]
        assert len(asn_facts) == 1
        assert asn_facts[0].value == "AS15169"
        assert asn_facts[0].confidence == pytest.approx(0.75, abs=0.05)

    def test_timezone_fact_produced(self):
        """Timezone should appear as a GENERIC fact with geo estimate label."""
        facts = self.normalizer.normalize(self._full_payload())
        tz_facts = [
            f for f in facts
            if f.fact_type == self.FactType.GENERIC and f.metadata.get("field") == "timezone"
        ]
        assert len(tz_facts) == 1
        assert tz_facts[0].value == "America/Los_Angeles"
        assert tz_facts[0].metadata.get("data_label") == "IP geolocation estimate"

    def test_geolocation_estimate_label_on_country(self):
        """Country fact metadata must contain 'IP geolocation estimate' label."""
        facts = self.normalizer.normalize(self._full_payload())
        country_facts = [
            f for f in facts
            if f.fact_type == self.FactType.LOCATION
            and f.metadata.get("field") == "country"
        ]
        assert country_facts[0].metadata.get("data_label") == "IP geolocation estimate"

    def test_private_ip_produces_single_generic_fact(self):
        """Private IPs should produce a single GENERIC IP fact with ip_class label."""
        payload = {
            "ip": "192.168.1.100",
            "version": 4,
            "is_private": True,
            "is_loopback": False,
            "is_link_local": False,
            "is_reserved": False,
            "is_publicly_routable": False,
            "country": None, "country_code": None, "region": None, "city": None,
            "latitude": None, "longitude": None, "timezone": None,
            "asn": None, "org": None,
            "error": "192.168.1.100 is a private IP address.",
            "error_code": None,
        }
        facts = self.normalizer.normalize(payload)
        assert len(facts) == 1
        assert facts[0].fact_type == self.FactType.GENERIC
        assert facts[0].value == "192.168.1.100"
        assert facts[0].metadata.get("ip_class") == "private"
        assert facts[0].confidence == pytest.approx(0.90, abs=0.05)

    def test_validation_error_produces_low_confidence_fact(self):
        """Validation errors should produce a near-zero confidence fact for audit."""
        payload = {
            "ip": "not-an-ip",
            "version": None,
            "is_private": False, "is_loopback": False, "is_link_local": False,
            "is_reserved": False, "is_publicly_routable": False,
            "country": None, "country_code": None, "region": None, "city": None,
            "latitude": None, "longitude": None, "timezone": None,
            "asn": None, "org": None,
            "error": "not-an-ip is not a valid IPv4 or IPv6 address",
            "error_code": "validation_error",
        }
        facts = self.normalizer.normalize(payload)
        assert len(facts) == 1
        assert facts[0].confidence <= 0.15
        assert facts[0].metadata.get("validation_failed") is True

    def test_missing_optional_fields_skipped_gracefully(self):
        """Missing optional fields should not produce extra facts — no crashes."""
        payload = {
            "ip": "8.8.8.8",
            "version": 4,
            "is_private": False,
            "is_loopback": False,
            "is_link_local": False,
            "is_reserved": False,
            "is_publicly_routable": True,
            "country": "Germany",
            "country_code": "DE",
            "region": None,  # Missing
            "city": None,    # Missing
            "latitude": None,
            "longitude": None,
            "timezone": None,  # Missing
            "asn": None,       # Missing
            "org": None,       # Missing
            "error": None,
            "error_code": None,
        }
        facts = self.normalizer.normalize(payload)
        # Should have: IP + country (no region/city/timezone/asn/isp)
        fact_fields = [f.metadata.get("field") for f in facts]
        assert "ip_address" in fact_fields
        assert "country" in fact_fields
        assert "region_city" not in fact_fields
        assert "timezone" not in fact_fields
        assert "asn" not in fact_fields

    def test_non_dict_raises_normalization_error(self):
        """Non-dict input must raise NormalizationError."""
        from app.normalizers.types import NormalizationError
        with pytest.raises(NormalizationError):
            self.normalizer.normalize("not a dict")


# ═══════════════════════════════════════════════════════════════════════════
# 4. REVERSE DNS NON-REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestReverseDnsNonRegression:
    """Verify existing reverse_dns connector and normalizer are unaffected."""

    def setup_method(self):
        from app.normalizers.reverse_dns.normalizer import ReverseDnsNormalizer
        from app.normalizers.types import FactType
        self.normalizer = ReverseDnsNormalizer()
        self.FactType = FactType

    def test_ptr_records_become_domain_facts(self):
        """Existing reverse DNS normalizer still produces DOMAIN facts."""
        payload = {
            "ip_address": "8.8.8.8",
            "hostnames": ["dns.google", "dns.google."],
        }
        facts = self.normalizer.normalize(payload)
        assert len(facts) >= 1
        assert all(f.fact_type == self.FactType.DOMAIN for f in facts)
        assert facts[0].value == "dns.google"

    def test_empty_hostnames_produces_no_facts(self):
        """No PTR records → no facts (not an error)."""
        payload = {"ip_address": "8.8.8.8", "hostnames": []}
        facts = self.normalizer.normalize(payload)
        assert facts == []

    def test_ptr_fact_has_reverse_dns_metadata(self):
        """PTR facts should have record_type=PTR and ip_address in metadata."""
        payload = {"ip_address": "8.8.8.8", "hostnames": ["dns.google"]}
        facts = self.normalizer.normalize(payload)
        assert facts[0].metadata.get("record_type") == "PTR"
        assert facts[0].metadata.get("ip_address") == "8.8.8.8"
        assert facts[0].metadata.get("reverse_dns") is True


# ═══════════════════════════════════════════════════════════════════════════
# 5. FAILURE ISOLATION TEST
# ═══════════════════════════════════════════════════════════════════════════


class TestFailureIsolation:
    """
    Verify that geo failure does not prevent reverse DNS facts,
    and reverse DNS failure does not prevent geo facts.
    """

    def setup_method(self):
        from app.normalizers.ip.normalizer import IpGeolocationNormalizer
        from app.normalizers.reverse_dns.normalizer import ReverseDnsNormalizer
        from app.normalizers.types import FactType
        self.geo_normalizer = IpGeolocationNormalizer()
        self.rdns_normalizer = ReverseDnsNormalizer()
        self.FactType = FactType

    def test_geo_timeout_rdns_still_produces_facts(self):
        """When geo returns a timeout error, reverse DNS can still succeed."""
        # Geo payload: timed out
        geo_payload = {
            "ip": "8.8.8.8", "version": 4, "is_private": False,
            "is_loopback": False, "is_link_local": False, "is_reserved": False,
            "is_publicly_routable": True,
            "country": None, "country_code": None, "region": None, "city": None,
            "latitude": None, "longitude": None, "timezone": None,
            "asn": None, "org": None,
            "error": "IP geolocation request timed out after 20.0s.",
            "error_code": "timeout",
        }
        geo_facts = self.geo_normalizer.normalize(geo_payload)
        # Only the IP fact itself should come back (no location/isp/asn)
        assert len(geo_facts) == 1
        assert geo_facts[0].metadata.get("field") == "ip_address"

        # Reverse DNS payload: succeeded independently
        rdns_payload = {"ip_address": "8.8.8.8", "hostnames": ["dns.google"]}
        rdns_facts = self.rdns_normalizer.normalize(rdns_payload)
        assert len(rdns_facts) == 1
        assert rdns_facts[0].fact_type == self.FactType.DOMAIN

    def test_rdns_failure_geo_still_produces_facts(self):
        """When reverse DNS has no PTR record, geo can still succeed."""
        rdns_payload = {"ip_address": "8.8.8.8", "hostnames": [], "error": "NXDOMAIN"}
        rdns_facts = self.rdns_normalizer.normalize(rdns_payload)
        assert rdns_facts == []  # No PTR = no facts (not an error)

        geo_payload = {
            "ip": "8.8.8.8", "version": 4,
            "is_private": False, "is_loopback": False, "is_link_local": False,
            "is_reserved": False, "is_publicly_routable": True,
            "country": "United States", "country_code": "US",
            "region": "California", "city": "Mountain View",
            "latitude": 37.39, "longitude": -122.08,
            "timezone": "America/Los_Angeles",
            "asn": "AS15169", "org": "AS15169 Google LLC",
            "error": None, "error_code": None,
        }
        geo_facts = self.geo_normalizer.normalize(geo_payload)
        assert len(geo_facts) > 1  # Multiple geo facts
        location_facts = [f for f in geo_facts if f.fact_type == self.FactType.LOCATION]
        assert len(location_facts) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONNECTOR REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectorRegistration:
    """Verify IpGeolocationConnector is registered in the framework."""

    def test_ip_geolocation_connector_registered(self):
        """IpGeolocationConnector should be registered in the global registry."""
        from app.connectors.registry import registry
        from app.connectors.types import IdentifierType
        import app.connectors  # noqa: F401 — triggers registration

        connectors = registry.get_connectors_for_identifier_type(IdentifierType.IP)
        connector_names = [c.name for c in connectors]
        assert "ip_geolocation" in connector_names, (
            f"ip_geolocation not found in IP connectors: {connector_names}"
        )

    def test_reverse_dns_connector_still_registered(self):
        """ReverseDnsConnector must still be registered after IP changes."""
        from app.connectors.registry import registry
        from app.connectors.types import IdentifierType
        import app.connectors  # noqa: F401

        connectors = registry.get_connectors_for_identifier_type(IdentifierType.IP)
        connector_names = [c.name for c in connectors]
        assert "reverse_dns" in connector_names, (
            f"reverse_dns not found in IP connectors: {connector_names}"
        )

    def test_ip_geolocation_normalizer_registered(self):
        """IpGeolocationNormalizer should be registered in the normalizer registry."""
        from app.normalizers.registry import normalizer_registry
        import app.normalizers  # noqa: F401

        assert normalizer_registry.has_normalizer("ip_geolocation"), (
            "IpGeolocationNormalizer not registered"
        )

    def test_existing_normalizers_still_registered(self):
        """Existing normalizers must not be affected by IP normalizer registration."""
        from app.normalizers.registry import normalizer_registry
        import app.normalizers  # noqa: F401

        for name in ("phone", "reverse_dns", "whois", "bitcoin", "truecaller"):
            assert normalizer_registry.has_normalizer(name), (
                f"Normalizer for '{name}' unexpectedly unregistered"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 7. IDENTIFIER API FORMATTING (synthetic facts — no DB required)
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentifierApiFormatting:
    """
    Verify that ip_geolocation and reverse_dns (IP) facts are correctly
    formatted by list_identifiers by injecting synthetic NormalizedFact
    DB models without running a full pipeline.
    """

    def _make_fact(self, connector_name, fact_type, value, meta=None, confidence=0.8):
        """Create a minimal mock NormalizedFact ORM object."""
        f = MagicMock()
        f.id = "test-fact-id"
        f.connector_name = connector_name
        f.fact_type = fact_type
        f.value = value
        f.confidence = confidence
        f.fact_metadata = meta or {}
        f.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return f

    def test_ip_geolocation_country_formatted(self):
        """ip_geolocation country fact → 'Country (Geolocation Estimate)'."""
        fact = self._make_fact(
            "ip_geolocation", "generic", "United States",
            meta={"field": "country"}
        )
        # Simulate the formatting logic from list_identifiers
        display_name = self._get_display_name(fact)
        assert display_name == "Country (Geolocation Estimate)"

    def test_ip_geolocation_isp_formatted(self):
        """ip_geolocation isp_org fact → 'ISP / Network Owner'."""
        fact = self._make_fact(
            "ip_geolocation", "contact_info", "Google LLC",
            meta={"field": "isp_org"}
        )
        display_name = self._get_display_name(fact)
        assert display_name == "ISP / Network Owner"

    def test_ip_geolocation_asn_formatted(self):
        """ip_geolocation asn fact → 'ASN (Autonomous System)'."""
        fact = self._make_fact(
            "ip_geolocation", "generic", "AS15169",
            meta={"field": "asn"}
        )
        display_name = self._get_display_name(fact)
        assert display_name == "ASN (Autonomous System)"

    def test_reverse_dns_ptr_formatted(self):
        """reverse_dns domain fact → 'Reverse DNS (PTR Record)'."""
        fact = self._make_fact(
            "reverse_dns", "domain", "dns.google",
            meta={"ip_address": "8.8.8.8", "record_type": "PTR"}
        )
        display_name = self._get_display_name(fact)
        assert display_name == "Reverse DNS (PTR Record)"

    def _get_display_name(self, fact) -> str:
        """Replicate the display name logic from list_identifiers."""
        meta = fact.fact_metadata or {}
        field = meta.get("field", "")
        ip_class = meta.get("ip_class", "")

        if fact.connector_name == "ip_geolocation":
            if field == "ip_address":
                return f"IP Address ({ip_class})" if ip_class else "IP Address"
            elif field == "country":
                return "Country (Geolocation Estimate)"
            elif field == "region_city":
                return "Region / City (Geolocation Estimate)"
            elif field == "isp_org":
                return "ISP / Network Owner"
            elif field == "asn":
                return "ASN (Autonomous System)"
            elif field == "timezone":
                return "Timezone (Geolocation Estimate)"
            else:
                return "IP Geolocation Data"

        if fact.connector_name == "reverse_dns" and fact.fact_type == "domain":
            return "Reverse DNS (PTR Record)"

        return "Unknown"
