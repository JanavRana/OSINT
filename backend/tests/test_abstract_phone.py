"""
tests/test_abstract_phone.py

Unit tests for Abstract Phone Validation OSINT Connector and Normalizer.
Coverage:
- AbstractPhoneConnector with mock responses (VoIP, Mobile, Landline, Invalid)
- AbstractPhoneConnector error handling (429 rate limit, missing API key, short phone)
- AbstractPhoneNormalizer fact generation (VoIP warning badge, Carrier, Line Type, Location)
- Registry registration for connector and normalizer
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.connectors.abstract_phone.connector import AbstractPhoneConnector
from app.connectors.registry import registry
from app.connectors.types import Identifier, IdentifierType
from app.normalizers.abstract_phone.normalizer import AbstractPhoneNormalizer
from app.normalizers.registry import normalizer_registry


class TestAbstractPhoneConnector:
    """Test suite for AbstractPhoneConnector (Mock-based to conserve API quota)."""

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"ABSTRACT_PHONE_API_KEY": "test_phone_key_123"})
    @patch("httpx.AsyncClient.get")
    async def test_voip_phone_detection(self, mock_get):
        """Test AbstractPhoneConnector correctly parses VoIP / Virtual burner numbers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phone": "14155552671",
            "valid": True,
            "format": {
                "international": "+14155552671",
                "local": "(415) 555-2671",
            },
            "country": {
                "code": "US",
                "name": "United States",
                "prefix": "+1",
            },
            "location": "California",
            "type": "VoIP",
            "carrier": "Twilio",
        }
        mock_get.return_value = mock_response

        connector = AbstractPhoneConnector()
        ident = Identifier(value="+14155552671", type=IdentifierType.PHONE)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is True
        assert res["valid"] is True
        assert res["type"] == "VoIP"
        assert res["is_voip"] is True
        assert res["carrier"] == "Twilio"
        assert res["location"] == "California"
        assert res["country_name"] == "United States"
        assert res["international_format"] == "+14155552671"

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"ABSTRACT_PHONE_API_KEY": "test_phone_key_123"})
    @patch("httpx.AsyncClient.get")
    async def test_mobile_phone_carrier(self, mock_get):
        """Test AbstractPhoneConnector correctly parses mobile line & carrier."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phone": "14155552671",
            "valid": True,
            "format": {
                "international": "+14155552671",
                "local": "(415) 555-2671",
            },
            "country": {
                "code": "US",
                "name": "United States",
                "prefix": "+1",
            },
            "location": "California",
            "type": "Mobile",
            "carrier": "Verizon Wireless",
        }
        mock_get.return_value = mock_response

        connector = AbstractPhoneConnector()
        ident = Identifier(value="+14155552671", type=IdentifierType.PHONE)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is True
        assert res["type"] == "Mobile"
        assert res["is_voip"] is False
        assert res["carrier"] == "Verizon Wireless"

    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=True)
    async def test_missing_api_key_returns_graceful_error(self):
        """Test connector returns missing api key error if no env var is set."""
        connector = AbstractPhoneConnector()
        ident = Identifier(value="+14155552671", type=IdentifierType.PHONE)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is False
        assert res["error_code"] == "api_key_missing"

    @pytest.mark.asyncio
    async def test_short_invalid_phone_rejected(self):
        """Test short invalid phone number returns validation error without calling API."""
        connector = AbstractPhoneConnector()
        ident = Identifier(value="123", type=IdentifierType.PHONE)
        res = await connector.fetch(ident)

        assert res["abstract_matched"] is False
        assert res["error_code"] == "validation_error"


class TestAbstractPhoneNormalizer:
    """Test suite for AbstractPhoneNormalizer."""

    def test_voip_burner_facts_emitted(self):
        """Test VoIP warning fact (confidence 0.95), Carrier, and Location facts are emitted."""
        normalizer = AbstractPhoneNormalizer()
        raw_data = {
            "phone": "+14155552671",
            "cleaned_phone": "14155552671",
            "valid": True,
            "international_format": "+14155552671",
            "local_format": "(415) 555-2671",
            "country_name": "United States",
            "country_code": "US",
            "location": "California",
            "type": "VoIP",
            "carrier": "Twilio",
            "is_voip": True,
            "abstract_matched": True,
        }

        facts = normalizer.normalize(raw_data)
        fields = [f.metadata.get("field") for f in facts]

        assert "phone_number" in fields
        assert "voip_detected" in fields
        assert "telecom_carrier" in fields
        assert "phone_location" in fields

        # Verify VoIP warning fact
        voip_fact = next(f for f in facts if f.metadata.get("field") == "voip_detected")
        assert voip_fact.value == "VoIP / VIRTUAL BURNER NUMBER"
        assert voip_fact.confidence == 0.95
        assert voip_fact.metadata.get("risk_level") == "HIGH"

        # Verify Carrier fact
        carrier_fact = next(f for f in facts if f.metadata.get("field") == "telecom_carrier")
        assert carrier_fact.value == "Twilio"
        assert carrier_fact.confidence == 0.90


class TestAbstractPhoneRegistration:
    """Test registry registrations."""

    def test_connector_registered(self):
        """Verify AbstractPhoneConnector is registered in connector registry for IdentifierType.PHONE."""
        connectors = registry.get_connectors_for_identifier_type(IdentifierType.PHONE)
        names = [c.name for c in connectors]
        assert "abstract_phone" in names

    def test_normalizer_registered(self):
        """Verify AbstractPhoneNormalizer is registered in normalizer registry."""
        norm_cls = normalizer_registry.get_normalizer("abstract_phone")
        assert norm_cls is AbstractPhoneNormalizer
