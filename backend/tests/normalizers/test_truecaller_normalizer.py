"""
tests/normalizers/test_truecaller_normalizer.py

Comprehensive test suite for TruecallerConnector and TruecallerNormalizer.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.connectors.truecaller.connector import TruecallerConnector
from app.connectors.types import Identifier, IdentifierType
from app.normalizers.truecaller.normalizer import TruecallerNormalizer
from app.normalizers.types import FactType


@pytest.mark.asyncio
async def test_truecaller_connector_not_configured():
    connector = TruecallerConnector()
    identifier = Identifier(value="+919944234127", type=IdentifierType.PHONE)
    mock_settings = MagicMock()
    mock_settings.truecaller_rapidapi_key = ""
    mock_settings.truecaller_rapidapi_host = ""
    with patch.dict("os.environ", {}, clear=True), patch("app.connectors.truecaller.connector.get_settings", return_value=mock_settings):
        result = await connector.fetch(identifier)
        assert result["name"] is None
        assert "not configured" in result["error"]


@pytest.mark.asyncio
async def test_truecaller_connector_success():
    connector = TruecallerConnector()
    identifier = Identifier(value="+919944234127", type=IdentifierType.PHONE)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "basicInfo": {
                "name": {
                    "fullName": "Rajesh Kumar"
                }
            },
            "internetInfo": {
                "email": "rajesh@example.com"
            },
            "addressInfo": {
                "city": "Chennai",
                "state": "Tamil Nadu",
                "countryCode": "IN"
            },
            "phoneInfo": {
                "carrier": "Airtel",
                "numberType": "MOBILE"
            },
            "badges": ["Verified"]
        }
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    with patch.dict("os.environ", {"TRUECALLER_RAPIDAPI_KEY": "testkey"}):
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await connector.fetch(identifier)
            assert result["name"] == "Rajesh Kumar"
            assert result["email"] == "rajesh@example.com"
            assert result["city"] == "Chennai"
            assert result["state"] == "Tamil Nadu"
            assert result["carrier"] == "Airtel"


def test_truecaller_normalizer():
    normalizer = TruecallerNormalizer()
    payload = {
        "name": "Rajesh Kumar",
        "email": "rajesh@example.com",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "IN",
        "carrier": "Airtel",
        "badge": "Verified",
    }

    facts = normalizer.normalize(payload)
    fact_types = [f.fact_type for f in facts]

    assert FactType.PROFILE_DATA in fact_types
    assert FactType.EMAIL in fact_types
    assert FactType.LOCATION in fact_types
    assert FactType.CONTACT_INFO in fact_types
    assert FactType.GENERIC in fact_types

    name_fact = next(f for f in facts if f.fact_type == FactType.PROFILE_DATA)
    assert name_fact.value == "Rajesh Kumar"
    assert name_fact.confidence == 0.85

    email_fact = next(f for f in facts if f.fact_type == FactType.EMAIL)
    assert email_fact.value == "rajesh@example.com"
    assert email_fact.confidence == 0.90
