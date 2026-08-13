"""
connectors/abstract_phone/connector.py

Abstract Phone Validation OSINT Connector.

Queries https://phonevalidation.abstractapi.com/v1/ to extract:
- Phone Validity & E.164 International Format
- Line Type Classification: Mobile, Landline, VoIP / Virtual (Burner)
- Telecom Carrier (e.g. Verizon Wireless, Jio, AT&T, Vodafone)
- Geographic Region / State / Country attached to area code
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, ClassVar, Dict, FrozenSet

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType

logger = logging.getLogger("osint-aggregator")


@registry.register
class AbstractPhoneConnector(BaseConnector):
    """
    Abstract Phone Validation OSINT Connector.

    Supports `IdentifierType.PHONE`.
    Queries Abstract API to extract telecom carrier, line type (VoIP vs Mobile vs Landline),
    and international formatting metadata.
    """

    name: ClassVar[str] = "abstract_phone"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.PHONE}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Clean phone number and query Abstract Phone Validation API.
        """
        raw_value = identifier.value.strip()
        # Basic digits & leading plus cleaning
        cleaned_phone = re.sub(r"[^\d+]", "", raw_value)

        result: Dict[str, Any] = {
            "phone": raw_value,
            "cleaned_phone": cleaned_phone,
            "valid": False,
            "international_format": None,
            "local_format": None,
            "country_name": None,
            "country_code": None,
            "country_prefix": None,
            "location": None,
            "type": None,
            "carrier": None,
            "is_voip": False,
            "abstract_matched": False,
            "error": None,
            "error_code": None,
        }

        if not cleaned_phone or len(re.sub(r"\D", "", cleaned_phone)) < 5:
            result["error"] = "Phone number is too short or invalid."
            result["error_code"] = "validation_error"
            return result

        # Check for API key
        api_key = os.environ.get("ABSTRACT_PHONE_API_KEY") or os.environ.get("ABSTRACT_API_KEY")
        if not api_key:
            logger.info("ABSTRACT_PHONE_API_KEY not configured; skipping Abstract Phone lookup.")
            result["error"] = "ABSTRACT_PHONE_API_KEY not set"
            result["error_code"] = "api_key_missing"
            return result

        # Query Abstract Phone API
        url = "https://phonevalidation.abstractapi.com/v1/"
        params = {"api_key": api_key.strip(), "phone": cleaned_phone}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    result["abstract_matched"] = True
                    result["valid"] = bool(data.get("valid", False))
                    result["location"] = data.get("location")
                    result["type"] = data.get("type")
                    result["carrier"] = data.get("carrier")

                    # Formats
                    fmt_data = data.get("format") or {}
                    if isinstance(fmt_data, dict):
                        result["international_format"] = fmt_data.get("international")
                        result["local_format"] = fmt_data.get("local")

                    # Country
                    ctry_data = data.get("country") or {}
                    if isinstance(ctry_data, dict):
                        result["country_name"] = ctry_data.get("name")
                        result["country_code"] = ctry_data.get("code")
                        result["country_prefix"] = ctry_data.get("prefix")

                    # Risk & Disposable Detection
                    risk_data = data.get("phone_risk") or {}
                    if isinstance(risk_data, dict):
                        result["is_disposable"] = bool(risk_data.get("is_disposable") or data.get("is_disposable"))
                        result["risk_level"] = risk_data.get("risk_level")
                        result["is_abuse_detected"] = bool(risk_data.get("is_abuse_detected"))
                    else:
                        result["is_disposable"] = bool(data.get("is_disposable"))
                        result["risk_level"] = data.get("risk_level")
                        result["is_abuse_detected"] = False

                    # Line Type Flags (VoIP / Virtual Burner Detection)
                    line_type_str = str(result["type"] or "").lower()
                    if "voip" in line_type_str or "virtual" in line_type_str or result["is_disposable"]:
                        result["is_voip"] = True


                elif resp.status_code in (401, 403):
                    logger.warning("Abstract Phone API unauthorized (%s) for %s - check API key", resp.status_code, cleaned_phone)
                    result["error"] = "Invalid or unverified API key"
                    result["error_code"] = resp.status_code
                elif resp.status_code == 429:
                    logger.warning("Abstract Phone API rate limit (429) for %s", cleaned_phone)
                    result["error"] = "Rate limit exceeded"
                    result["error_code"] = 429
                else:
                    logger.warning("Abstract Phone API error HTTP %s for %s", resp.status_code, cleaned_phone)
                    result["error"] = f"HTTP {resp.status_code}"
                    result["error_code"] = resp.status_code

        except httpx.TimeoutException:
            logger.warning("Abstract Phone API request timeout for %s", cleaned_phone)
            result["error"] = "Timeout"
            result["error_code"] = "timeout"
        except Exception as exc:
            logger.warning("Abstract Phone API query error for %s: %s", cleaned_phone, exc)
            result["error"] = str(exc)
            result["error_code"] = "provider_error"

        return result
