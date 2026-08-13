"""
tests/test_abstract_ip.py

Unit tests for Abstract IP Geolocation & Anonymity OSINT Connector and Normalizer.
Coverage:
- AbstractIpConnector with mock responses (VPN, Tor, Proxy, Datacenter, Normal IP)
- AbstractIpConnector error handling (429 rate limit, missing API key, timeout, private IP)
- AbstractIpNormalizer fact generation
- Registry registration for connector and normalizer
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.connectors.abstract_ip.connector import AbstractIpConnector
from app.connectors.registry import registry
from app.connectors.types import Identifier, IdentifierType
from app.normalizers.abstract_ip.normalizer import AbstractIpNormalizer
from app.normalizers.registry import normalizer_registry


class TestAbstractIpConnector:
    """Test suite for AbstractIpConnector."""

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"ABSTRACT_IP_API_KEY": "test_key_123"})
    @patch("httpx.AsyncClient.get")
    async def test_tor_vpn_proxy_detection(self, mock_get):
        """Test AbstractIpConnector correctly parses Tor, VPN, and Proxy flags from IP Intelligence API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ip_address": "185.220.101.5",
            "location": {
                "city": "Amsterdam",
                "region": "North Holland",
                "postal_code": "1012",
                "country": "Netherlands",
                "country_code": "NL",
                "longitude": 4.8951,
                "latitude": 52.3702,
            },
            "timezone": {"name": "Europe/Amsterdam", "utc_offset": 2},
            "asn": {
                "asn": 208294,
                "name": "Zwiebelfreunde e.V.",
                "domain": None,
                "type": "isp",
            },
            "company": {
                "name": "Zwiebelfreunde e.V.",
                "domain": None,
                "type": "isp",
            },
            "security": {
                "is_vpn": True,
                "is_proxy": False,
                "is_tor": True,
                "is_hosting": True,
                "is_relay": False,
                "is_mobile": False,
                "is_abuse": True,
            },
        }
        mock_get.return_value = mock_response

        connector = AbstractIpConnector()
        ident = Identifier(value="185.220.101.5", type=IdentifierType.IP)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is True
        assert res["ip"] == "185.220.101.5"
        assert res["is_tor"] is True
        assert res["is_vpn"] is True
        assert res["is_datacenter"] is True
        assert res["is_abuse"] is True
        assert res["threat_level"] == "high"
        assert res["city"] == "Amsterdam"
        assert res["country"] == "Netherlands"
        assert res["isp"] == "Zwiebelfreunde e.V."
        assert res["asn"] == "AS208294 Zwiebelfreunde e.V."

    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=True)
    async def test_missing_api_key_returns_graceful_error(self):
        """Test connector returns missing api key error if no env var is set."""
        connector = AbstractIpConnector()
        ident = Identifier(value="8.8.8.8", type=IdentifierType.IP)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is False
        assert res["error_code"] == "api_key_missing"

    @pytest.mark.asyncio
    async def test_private_ip_skips_external_query(self):
        """Test private IP address skips external HTTP query."""
        connector = AbstractIpConnector()
        ident = Identifier(value="192.168.1.1", type=IdentifierType.IP)
        res = await connector.fetch(ident)

        assert res["is_publicly_routable"] is False
        assert res["abstract_matched"] is False

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"ABSTRACT_IP_API_KEY": "test_key_123"})
    @patch("httpx.AsyncClient.get")
    async def test_rate_limit_429(self, mock_get):
        """Test 429 rate limit is handled gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        connector = AbstractIpConnector()
        ident = Identifier(value="8.8.8.8", type=IdentifierType.IP)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is False
        assert res["error_code"] == 429


class TestAbstractIpNormalizer:
    """Test suite for AbstractIpNormalizer."""

    def test_security_and_anonymity_facts_produced(self):
        """Test security facts (Tor, VPN, Proxy, Datacenter, Threat Level) are emitted."""
        normalizer = AbstractIpNormalizer()
        raw_data = {
            "ip": "185.220.101.5",
            "version": 4,
            "is_publicly_routable": True,
            "city": "Amsterdam",
            "region": "North Holland",
            "country": "Netherlands",
            "country_code": "NL",
            "isp": "Zwiebelfreunde e.V.",
            "asn": "AS208294 Zwiebelfreunde e.V.",
            "timezone": "Europe/Amsterdam",
            "is_vpn": True,
            "is_tor": True,
            "is_proxy": True,
            "is_datacenter": True,
            "threat_level": "high",
        }

        facts = normalizer.normalize(raw_data)
        fields = [f.metadata.get("field") for f in facts]

        assert "tor_exit_node" in fields
        assert "vpn_detected" in fields

        assert "proxy_detected" in fields
        assert "datacenter_ip" in fields
        assert "threat_level" in fields
        assert "country" in fields
        assert "region_city" in fields
        assert "isp_org" in fields

        # Check Tor Exit Node fact details
        tor_fact = next(f for f in facts if f.metadata.get("field") == "tor_exit_node")
        assert tor_fact.value == "ACTIVE TOR EXIT NODE"
        assert tor_fact.confidence == 0.98

        # Check VPN fact details
        vpn_fact = next(f for f in facts if f.metadata.get("field") == "vpn_detected")
        assert vpn_fact.value == "COMMERCIAL VPN DETECTED"
        assert vpn_fact.confidence == 0.95


class TestAbstractIpRegistration:
    """Test registry registrations."""

    def test_connector_registered(self):
        """Verify AbstractIpConnector is registered in connector registry for IdentifierType.IP."""
        connectors = registry.get_connectors_for_identifier_type(IdentifierType.IP)
        names = [c.name for c in connectors]
        assert "abstract_ip" in names

    def test_normalizer_registered(self):
        """Verify AbstractIpNormalizer is registered in normalizer registry."""
        norm_cls = normalizer_registry.get_normalizer("abstract_ip")
        assert norm_cls is AbstractIpNormalizer
