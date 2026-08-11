"""
connectors/truecaller/connector.py

Truecaller OSINT connector using RapidAPI proxy endpoint.

This connector:
    1. Subclasses BaseConnector and registers via @registry.register.
    2. Accepts only PHONE identifiers.
    3. Uses HTTPX to query the RapidAPI Truecaller proxy API asynchronously.
    4. Configured via environment variables:
       - TRUECALLER_RAPIDAPI_KEY or RAPIDAPI_KEY
       - TRUECALLER_RAPIDAPI_HOST (defaults to 'truecaller-data2.p.rapidapi.com')
    5. Returns a raw JSON dictionary containing Truecaller profile details
       (Name, Email, Address/City/State, Carrier, Badges/Spam) for normalization.
    6. Gracefully returns an error dict if not configured or not subscribed,
       ensuring partial investigation pipeline execution is never stalled.
"""

from __future__ import annotations

import os
import re
from typing import Any, ClassVar, Dict, FrozenSet

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType


from app.core.config import get_settings


@registry.register
class TruecallerConnector(BaseConnector):
    """
    Truecaller OSINT connector — queries RapidAPI Truecaller endpoint to
    retrieve caller identification, names, emails, and address metadata.
    """

    name: ClassVar[str] = "truecaller"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.PHONE}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Fetch caller identification data from Truecaller via RapidAPI.

        Args:
            identifier: A PHONE identifier string (e.g. "+91 9944234127" or "+14155552671").

        Returns:
            JSON-serializable dict containing Truecaller search response or error info.
        """
        settings = get_settings()
        api_key = (
            os.getenv("TRUECALLER_RAPIDAPI_KEY")
            or os.getenv("RAPIDAPI_KEY")
            or settings.truecaller_rapidapi_key
        )
        api_host = (
            os.getenv("TRUECALLER_RAPIDAPI_HOST")
            or settings.truecaller_rapidapi_host
            or "truecaller-data2.p.rapidapi.com"
        )

        raw_input = identifier.value.strip()
        # Clean digits for Truecaller API (remove +, spaces, dashes)
        clean_digits = re.sub(r"\D", "", raw_input)

        result: Dict[str, Any] = {
            "input": raw_input,
            "clean_digits": clean_digits,
            "name": None,
            "email": None,
            "address": None,
            "city": None,
            "state": None,
            "country": None,
            "carrier": None,
            "line_type": None,
            "badge": None,
            "score": None,
            "raw_response": None,
            "error": None,
        }

        if not api_key:
            result["error"] = "TRUECALLER_RAPIDAPI_KEY or RAPIDAPI_KEY not configured in environment"
            return result

        # Truecaller RapidAPI URL endpoint pattern
        url = f"https://{api_host}/search/{clean_digits}"
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": api_host,
            "x-rapidapi-key": api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 403:
                    result["error"] = "RapidAPI 403: Not subscribed to Truecaller API or key invalid"
                    return result
                elif response.status_code != 200:
                    result["error"] = f"RapidAPI HTTP Error {response.status_code}: {response.text}"
                    return result

                data = response.json()
                result["raw_response"] = data

                # Parse standard Truecaller response payloads
                self._parse_response(data, result)

        except httpx.TimeoutException:
            result["error"] = f"Truecaller RapidAPI query timed out after {self.timeout_seconds}s"
        except Exception as exc:
            result["error"] = f"Truecaller query failed: {exc}"

        return result

    def _parse_response(self, data: Any, result: Dict[str, Any]) -> None:
        """Helper to extract Truecaller API JSON response fields."""
        if not isinstance(data, dict):
            return

        payload = data.get("data")
        if not isinstance(payload, dict):
            # Fall back if data is at root or list
            records = data.get("results") or [data]
            if isinstance(records, list) and records and isinstance(records[0], dict):
                payload = records[0]
            else:
                return

        # Basic Info (Name, Image)
        basic_info = payload.get("basicInfo") or {}
        if isinstance(basic_info, dict):
            name_obj = basic_info.get("name") or {}
            if isinstance(name_obj, dict):
                full_name = name_obj.get("fullName") or name_obj.get("altName")
                if not full_name:
                    first = name_obj.get("firstName") or ""
                    last = name_obj.get("lastName") or ""
                    full_name = f"{first} {last}".strip()
                result["name"] = full_name if full_name else None
            elif isinstance(name_obj, str):
                result["name"] = name_obj.strip()

            result["image"] = basic_info.get("image")
        elif isinstance(payload.get("name"), str):
            result["name"] = payload["name"].strip()

        # Address Info (City, State, Country, Zip)
        addr_info = payload.get("addressInfo") or payload.get("location") or {}
        if isinstance(addr_info, dict):
            result["city"] = addr_info.get("city")
            result["state"] = addr_info.get("state") or addr_info.get("area")
            result["country"] = addr_info.get("countryCode") or addr_info.get("country")
            result["address"] = addr_info.get("address") or addr_info.get("street")

        # Internet Info (Email)
        net_info = payload.get("internetInfo") or {}
        if isinstance(net_info, dict):
            email_obj = net_info.get("email") or net_info.get("emails")
            if isinstance(email_obj, dict):
                result["email"] = email_obj.get("id") or email_obj.get("email")
            elif isinstance(email_obj, list) and email_obj:
                first_e = email_obj[0]
                if isinstance(first_e, dict):
                    result["email"] = first_e.get("id") or first_e.get("email")
                else:
                    result["email"] = str(first_e)
            elif isinstance(email_obj, str):
                result["email"] = email_obj

        # Phone Info (Carrier, Line Type, Spam)
        phone_info = payload.get("phoneInfo") or {}
        if isinstance(phone_info, dict):
            result["carrier"] = phone_info.get("carrier")
            result["line_type"] = phone_info.get("numberType") or phone_info.get("type")
            result["spam_type"] = phone_info.get("spamType")
            result["spam_score"] = phone_info.get("spamScore")

        # Badges & Tags
        badges = payload.get("badges") or []
        tags = payload.get("tags") or []
        badge_list = []
        if isinstance(badges, list):
            badge_list.extend(badges)
        if isinstance(tags, list):
            badge_list.extend(tags)

        result["badge"] = ", ".join(badge_list) if badge_list else None
        result["score"] = payload.get("score")
