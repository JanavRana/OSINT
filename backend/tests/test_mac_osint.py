"""
tests/test_mac_osint.py

Comprehensive unit tests for MAC Address & Wigle.net OSINT:
    - MAC validator (colon, hyphen, Cisco dot, bare hex, invalid strings)
    - MacOsintConnector (mocked OUI lookup + mocked Wigle API)
    - MacNormalizer (fact extraction, confidence scores, provenance labels)
    - Connector & normalizer registry verification
    - Failure isolation (missing Wigle API key does not fail vendor lookup)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════════════
# 1. VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestMacValidator:
    def setup_method(self):
        from app.connectors.mac.validator import validate_mac_address, MacValidationError
        self.validate = validate_mac_address
        self.MacValidationError = MacValidationError

    def test_colon_notation(self):
        result = self.validate("00:1A:2B:3C:4D:5E")
        assert result.normalized == "00:1A:2B:3C:4D:5E"
        assert result.oui_prefix == "00:1A:2B"

    def test_hyphen_notation(self):
        result = self.validate("00-11-22-33-44-55")
        assert result.normalized == "00:11:22:33:44:55"
        assert result.oui_prefix == "00:11:22"

    def test_cisco_dot_notation(self):
        result = self.validate("001a.2b3c.4d5e")
        assert result.normalized == "00:1A:2B:3C:4D:5E"
        assert result.oui_prefix == "00:1A:2B"

    def test_bare_hex_notation(self):
        result = self.validate("001122334455")
        assert result.normalized == "00:11:22:33:44:55"

    def test_lowercase_normalized_to_uppercase(self):
        result = self.validate("00:1a:2b:3c:4d:5e")
        assert result.normalized == "00:1A:2B:3C:4D:5E"

    def test_invalid_length_rejected(self):
        with pytest.raises(self.MacValidationError):
            self.validate("00:1A:2B:3C")

    def test_invalid_chars_rejected(self):
        with pytest.raises(self.MacValidationError):
            self.validate("00:1G:2H:3I:4J:5K")

    def test_empty_string_rejected(self):
        with pytest.raises(self.MacValidationError):
            self.validate("")


# ═══════════════════════════════════════════════════════════════════════════
# 2. CONNECTOR TESTS (Mocked HTTP)
# ═══════════════════════════════════════════════════════════════════════════


class TestMacOsintConnector:
    def setup_method(self):
        from app.connectors.mac.connector import MacOsintConnector
        from app.connectors.types import Identifier, IdentifierType
        self.connector = MacOsintConnector()
        self.Identifier = Identifier
        self.IdentifierType = IdentifierType

    def test_builtin_oui_apple_lookup(self):
        """Apple OUI 00:03:93 should resolve offline without HTTP calls."""
        ident = self.Identifier(value="00:03:93:11:22:33", type=self.IdentifierType.MAC)
        result = run(self.connector.fetch(ident))
        assert result["normalized_mac"] == "00:03:93:11:22:33"
        assert result["vendor"] == "Apple, Inc."
        assert result["error"] is None

    def test_builtin_oui_cisco_lookup(self):
        """Cisco OUI 00:00:0C should resolve offline."""
        ident = self.Identifier(value="00:00:0C:12:34:56", type=self.IdentifierType.MAC)
        result = run(self.connector.fetch(ident))
        assert result["vendor"] == "Cisco Systems, Inc."

    @patch("httpx.AsyncClient")
    def test_wigle_lookup_when_env_vars_set(self, mock_client_cls):
        """Wigle.net should be queried when WIGLE_API_NAME and WIGLE_API_TOKEN are set."""
        import os

        mock_wigle_resp = MagicMock()
        mock_wigle_resp.status_code = 200
        mock_wigle_resp.json.return_value = {
            "results": [
                {
                    "ssid": "Test_Guest_WiFi",
                    "triglat": 37.7749,
                    "triglon": -122.4194,
                    "country": "US",
                    "region": "California",
                    "city": "San Francisco",
                    "channel": 6,
                    "encryption": "WPA2",
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_wigle_resp)
        mock_client_cls.return_value = mock_client

        ident = self.Identifier(value="00:14:6C:7E:40:80", type=self.IdentifierType.MAC)
        env = {"WIGLE_API_NAME": "AID123", "WIGLE_API_TOKEN": "tok456"}

        with patch.dict(os.environ, env):
            result = run(self.connector.fetch(ident))

        assert result["vendor"] == "NETGEAR, Inc."
        assert result["wigle_matched"] is True
        assert result["ssid"] == "Test_Guest_WiFi"
        assert result["latitude"] == 37.7749
        assert result["city"] == "San Francisco"


# ═══════════════════════════════════════════════════════════════════════════
# 3. NORMALIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestMacNormalizer:
    def setup_method(self):
        from app.normalizers.mac.normalizer import MacNormalizer
        from app.normalizers.types import FactType
        self.normalizer = MacNormalizer()
        self.FactType = FactType

    def test_vendor_and_mac_facts(self):
        raw_payload = {
            "mac": "00:14:6C:7E:40:80",
            "normalized_mac": "00:14:6C:7E:40:80",
            "oui_prefix": "00:14:6C",
            "vendor": "NETGEAR, Inc.",
            "wigle_matched": False,
        }
        facts = self.normalizer.normalize(raw_payload)

        mac_facts = [f for f in facts if f.metadata.get("field") == "mac_address"]
        assert len(mac_facts) == 1
        assert mac_facts[0].value == "00:14:6C:7E:40:80"

        vendor_facts = [f for f in facts if f.fact_type == self.FactType.ORGANIZATION]
        assert len(vendor_facts) == 1
        assert vendor_facts[0].value == "NETGEAR, Inc."

    def test_wigle_location_facts(self):
        raw_payload = {
            "mac": "00:14:6C:7E:40:80",
            "normalized_mac": "00:14:6C:7E:40:80",
            "oui_prefix": "00:14:6C",
            "vendor": "NETGEAR, Inc.",
            "wigle_matched": True,
            "ssid": "CoffeeShop_5G",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "city": "New York",
            "region": "New York",
            "country": "United States",
            "encryption": "WPA2-PSK",
        }
        facts = self.normalizer.normalize(raw_payload)

        loc_facts = [f for f in facts if f.fact_type == self.FactType.LOCATION]
        assert len(loc_facts) == 1
        assert "New York" in loc_facts[0].value
        assert loc_facts[0].metadata.get("data_label") == "Wigle Wi-Fi BSSID Geolocation"

        ssid_facts = [f for f in facts if f.metadata.get("field") == "wifi_ssid"]
        assert len(ssid_facts) == 1
        assert ssid_facts[0].value == "CoffeeShop_5G"


# ═══════════════════════════════════════════════════════════════════════════
# 4. REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestMacRegistration:
    def test_connector_and_normalizer_registered(self):
        from app.connectors.registry import registry
        from app.normalizers.registry import normalizer_registry
        from app.connectors.types import IdentifierType
        import app.connectors  # noqa: F401
        import app.normalizers  # noqa: F401

        mac_connectors = registry.get_connectors_for_identifier_type(IdentifierType.MAC)
        names = [c.name for c in mac_connectors]
        assert "mac_osint" in names
        assert normalizer_registry.has_normalizer("mac_osint")
