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
        # Extract digits and ensure leading + prefix required by Abstract API
        digits_only = re.sub(r"\D", "", raw_value)
        cleaned_phone = f"+{digits_only}" if digits_only else raw_value

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

        # Query Abstract Phone Intelligence API
        url = "https://phoneintelligence.abstractapi.com/v1/"
        params = {"api_key": api_key.strip(), "phone": cleaned_phone}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    result["abstract_matched"] = True

                    # 1. Validation block
                    val_data = data.get("phone_validation") or {}
                    if isinstance(val_data, dict) and "is_valid" in val_data:
                        result["valid"] = bool(val_data.get("is_valid"))
                        result["is_voip"] = bool(val_data.get("is_voip"))
                    else:
                        result["valid"] = bool(data.get("valid", False))

                    # 2. Formats block
                    fmt_data = data.get("phone_format") or data.get("format") or {}
                    if isinstance(fmt_data, dict):
                        result["international_format"] = fmt_data.get("international")
                        result["local_format"] = fmt_data.get("national") or fmt_data.get("local")

                    # 3. Carrier & Line type block
                    carr_data = data.get("phone_carrier") or {}
                    if isinstance(carr_data, dict) and "name" in carr_data:
                        result["carrier"] = carr_data.get("name")
                        result["type"] = carr_data.get("line_type")
                    else:
                        result["carrier"] = data.get("carrier")
                        result["type"] = data.get("type")

                    # 4. Location block
                    loc_data = data.get("phone_location") or {}
                    if isinstance(loc_data, dict) and "country_name" in loc_data:
                        result["country_name"] = loc_data.get("country_name")
                        result["country_code"] = loc_data.get("country_code")
                        result["country_prefix"] = loc_data.get("country_prefix")
                        city = loc_data.get("city")
                        region = loc_data.get("region")
                        loc_parts = [p for p in [city, region] if p and str(p).strip() and str(p).strip().lower() != str(loc_data.get("country_name")).lower()]
                        result["location"] = ", ".join(loc_parts) if loc_parts else region or city
                    else:
                        result["location"] = data.get("location")
                        ctry_data = data.get("country") or {}
                        if isinstance(ctry_data, dict):
                            result["country_name"] = ctry_data.get("name")
                            result["country_code"] = ctry_data.get("code")
                            result["country_prefix"] = ctry_data.get("prefix")

                    # 5. Risk & Disposable Detection
                    risk_data = data.get("phone_risk") or {}
                    if isinstance(risk_data, dict) and "risk_level" in risk_data:
                        result["is_disposable"] = bool(risk_data.get("is_disposable"))
                        result["risk_level"] = risk_data.get("risk_level")
                        result["is_abuse_detected"] = bool(risk_data.get("is_abuse_detected"))
                    else:
                        result["is_disposable"] = bool(data.get("is_disposable"))
                        result["risk_level"] = data.get("risk_level")
                        result["is_abuse_detected"] = False

                    # 6. Messaging block
                    msg_data = data.get("phone_messaging") or {}
                    if isinstance(msg_data, dict):
                        result["sms_email"] = msg_data.get("sms_email")

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
