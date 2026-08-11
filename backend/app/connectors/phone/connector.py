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

        # ── Region & State precision ───────────────────────────────────────
        region = phonenumbers.region_code_for_number(parsed)
        result["region"] = region  # ISO alpha-2 country code e.g. "IN", "US", "GB"

        # For Indian numbers (+91 or region IN), derive state/circle location
        if parsed.country_code == 91 or region == "IN":
            result["state_region"] = self._get_indian_location(parsed)
        else:
            result["state_region"] = region

        # ── Carrier (100% native from phonenumbers library) ───────────────
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

    def _get_indian_location(self, parsed: phonenumbers.PhoneNumber) -> str:
        """
        Derive state / telecom circle for Indian numbers (+91 / IN).
        Checks fixed-line geocoder first, then 4-digit and 3-digit mobile prefix matrix.
        """
        # Fixed-line geocoder returns city/state (e.g. "Ahmedabad Local, Gujarat")
        geo_desc = geocoder.description_for_number(parsed, "en")
        if geo_desc and geo_desc != "India":
            return f"{geo_desc}, India" if "India" not in geo_desc else geo_desc

        # Mobile prefix series lookup (check 4-digit then 3-digit)
        national_str = str(parsed.national_number)
        for prefix_len in (4, 3):
            prefix = national_str[:prefix_len]
            state_name = _INDIAN_MOBILE_STATES.get(prefix)
            if state_name:
                return f"{state_name}, India"

        return "India"


# State / Telecom circle mapping for prefixes of Indian mobile numbers (+91 / IN)
_INDIAN_MOBILE_STATES: Dict[str, str] = {
    # ── Gujarat ──────────────────────────────────────────────────────────
    "9825": "Gujarat", "9898": "Gujarat", "9909": "Gujarat", "9979": "Gujarat",
    "9727": "Gujarat", "9426": "Gujarat", "8141": "Gujarat", "9099": "Gujarat",
    "7600": "Gujarat", "9925": "Gujarat", "9824": "Gujarat", "9978": "Gujarat",
    "9427": "Gujarat", "9723": "Gujarat", "9724": "Gujarat", "9725": "Gujarat",
    "9726": "Gujarat", "8866": "Gujarat", "8849": "Gujarat", "9510": "Gujarat", "9512": "Gujarat",
    "7016": "Gujarat", "7041": "Gujarat", "7043": "Gujarat", "7046": "Gujarat",
    "7048": "Gujarat", "7069": "Gujarat", "7096": "Gujarat", "7201": "Gujarat",
    "7202": "Gujarat", "7203": "Gujarat", "7359": "Gujarat", "7383": "Gujarat",
    "7405": "Gujarat", "7567": "Gujarat", "7572": "Gujarat", "7573": "Gujarat",
    "7574": "Gujarat", "7575": "Gujarat", "7621": "Gujarat", "7622": "Gujarat",
    "7623": "Gujarat", "7698": "Gujarat", "7801": "Gujarat", "7802": "Gujarat",
    "7817": "Gujarat", "7818": "Gujarat", "7819": "Gujarat", "7820": "Gujarat",
    "7874": "Gujarat", "7878": "Gujarat", "7984": "Gujarat", "7990": "Gujarat",
    "8128": "Gujarat", "8140": "Gujarat", "8153": "Gujarat", "8154": "Gujarat",
    "8155": "Gujarat", "8156": "Gujarat", "8160": "Gujarat", "8200": "Gujarat",
    "8238": "Gujarat", "8320": "Gujarat", "8347": "Gujarat", "8401": "Gujarat",
    "8460": "Gujarat", "8469": "Gujarat", "8487": "Gujarat", "8488": "Gujarat",
    "8511": "Gujarat", "8733": "Gujarat", "8734": "Gujarat", "8735": "Gujarat",
    "8758": "Gujarat", "8780": "Gujarat", "8980": "Gujarat", "9016": "Gujarat",
    "9033": "Gujarat", "9081": "Gujarat", "9104": "Gujarat", "9106": "Gujarat",
    "9157": "Gujarat", "9173": "Gujarat", "9227": "Gujarat", "9228": "Gujarat",
    "9265": "Gujarat", "9313": "Gujarat", "9316": "Gujarat", "9327": "Gujarat",
    "9328": "Gujarat", "9374": "Gujarat", "9375": "Gujarat", "9376": "Gujarat",
    "9377": "Gujarat", "9601": "Gujarat", "9624": "Gujarat", "9638": "Gujarat",
    "9662": "Gujarat", "9687": "Gujarat", "9712": "Gujarat", "9714": "Gujarat",
    "9722": "Gujarat", "9737": "Gujarat", "9879": "Gujarat",

    # ── Tamil Nadu & Puducherry ──────────────────────────────────────────
    "9944": "Tamil Nadu", "9943": "Tamil Nadu", "9942": "Tamil Nadu", "9842": "Tamil Nadu",
    "9843": "Tamil Nadu", "9443": "Tamil Nadu", "9442": "Tamil Nadu", "9789": "Tamil Nadu",
    "9788": "Tamil Nadu", "9787": "Tamil Nadu", "9786": "Tamil Nadu", "9790": "Tamil Nadu",
    "9791": "Tamil Nadu", "9600": "Tamil Nadu", "9626": "Tamil Nadu", "9629": "Tamil Nadu",
    "9655": "Tamil Nadu", "9677": "Tamil Nadu", "9688": "Tamil Nadu", "9698": "Tamil Nadu",
    "9003": "Tamil Nadu", "9042": "Tamil Nadu", "9043": "Tamil Nadu", "9047": "Tamil Nadu",
    "9080": "Tamil Nadu", "9087": "Tamil Nadu", "9092": "Tamil Nadu", "9095": "Tamil Nadu",
    "9150": "Tamil Nadu", "9159": "Tamil Nadu", "9171": "Tamil Nadu", "9176": "Tamil Nadu",
    "9344": "Tamil Nadu", "9345": "Tamil Nadu", "9360": "Tamil Nadu", "9361": "Tamil Nadu",
    "9362": "Tamil Nadu", "9363": "Tamil Nadu", "9364": "Tamil Nadu", "9367": "Tamil Nadu",
    "9384": "Tamil Nadu", "9444": "Tamil Nadu", "9445": "Tamil Nadu", "9486": "Tamil Nadu",
    "9487": "Tamil Nadu", "9488": "Tamil Nadu", "9489": "Tamil Nadu", "9500": "Tamil Nadu",
    "9566": "Tamil Nadu", "9597": "Tamil Nadu", "8012": "Tamil Nadu", "8015": "Tamil Nadu",
    "8056": "Tamil Nadu", "8072": "Tamil Nadu", "8110": "Tamil Nadu", "8122": "Tamil Nadu",
    "8124": "Tamil Nadu", "8144": "Tamil Nadu", "8148": "Tamil Nadu", "8220": "Tamil Nadu",
    "8248": "Tamil Nadu", "8300": "Tamil Nadu", "8428": "Tamil Nadu", "8489": "Tamil Nadu",
    "8608": "Tamil Nadu", "8610": "Tamil Nadu", "8667": "Tamil Nadu", "8668": "Tamil Nadu",
    "8680": "Tamil Nadu", "8681": "Tamil Nadu", "8682": "Tamil Nadu", "8754": "Tamil Nadu",
    "8760": "Tamil Nadu", "8778": "Tamil Nadu", "8825": "Tamil Nadu", "8838": "Tamil Nadu",
    "8870": "Tamil Nadu", "8903": "Tamil Nadu", "8925": "Tamil Nadu", "8939": "Tamil Nadu",
    "8940": "Tamil Nadu", "7010": "Tamil Nadu", "7092": "Tamil Nadu", "7094": "Tamil Nadu",
    "7200": "Tamil Nadu", "7305": "Tamil Nadu", "7338": "Tamil Nadu", "7339": "Tamil Nadu",
    "7358": "Tamil Nadu", "7373": "Tamil Nadu", "7397": "Tamil Nadu", "7401": "Tamil Nadu",
    "7418": "Tamil Nadu", "7502": "Tamil Nadu", "7530": "Tamil Nadu", "7539": "Tamil Nadu",
    "7540": "Tamil Nadu", "7548": "Tamil Nadu", "7550": "Tamil Nadu", "7598": "Tamil Nadu",
    "7601": "Tamil Nadu", "7603": "Tamil Nadu", "7604": "Tamil Nadu", "7639": "Tamil Nadu",
    "7667": "Tamil Nadu", "7708": "Tamil Nadu", "7810": "Tamil Nadu", "7811": "Tamil Nadu",
    "7812": "Tamil Nadu", "7823": "Tamil Nadu", "7824": "Tamil Nadu", "7825": "Tamil Nadu",
    "7826": "Tamil Nadu", "7845": "Tamil Nadu", "7867": "Tamil Nadu", "7868": "Tamil Nadu",
    "7871": "Tamil Nadu", "7904": "Tamil Nadu", "6369": "Tamil Nadu", "6374": "Tamil Nadu",
    "6379": "Tamil Nadu", "6380": "Tamil Nadu", "6381": "Tamil Nadu", "6382": "Tamil Nadu",
    "6383": "Tamil Nadu", "6384": "Tamil Nadu", "6385": "Tamil Nadu",

    # ── Delhi & NCR ──────────────────────────────────────────────────────
    "9810": "Delhi & NCR", "9811": "Delhi & NCR", "9818": "Delhi & NCR", "9871": "Delhi & NCR",
    "9910": "Delhi & NCR", "9999": "Delhi & NCR", "8800": "Delhi & NCR", "9711": "Delhi & NCR",
    "9899": "Delhi & NCR", "9868": "Delhi & NCR", "9873": "Delhi & NCR", "9953": "Delhi & NCR",
    "9958": "Delhi & NCR", "9971": "Delhi & NCR", "9650": "Delhi & NCR", "9654": "Delhi & NCR",
    "9716": "Delhi & NCR", "9717": "Delhi & NCR", "9718": "Delhi & NCR", "9540": "Delhi & NCR",
    "9555": "Delhi & NCR", "9560": "Delhi & NCR", "9582": "Delhi & NCR", "9013": "Delhi & NCR",
    "9015": "Delhi & NCR", "9210": "Delhi & NCR", "9211": "Delhi & NCR", "9212": "Delhi & NCR",
    "9213": "Delhi & NCR", "9250": "Delhi & NCR", "9266": "Delhi & NCR", "9268": "Delhi & NCR",
    "9278": "Delhi & NCR", "9289": "Delhi & NCR", "9310": "Delhi & NCR", "9311": "Delhi & NCR",
    "9312": "Delhi & NCR", "9315": "Delhi & NCR", "9350": "Delhi & NCR", "8010": "Delhi & NCR",
    "8130": "Delhi & NCR", "8285": "Delhi & NCR", "8287": "Delhi & NCR", "8373": "Delhi & NCR",
    "8375": "Delhi & NCR", "8376": "Delhi & NCR", "8377": "Delhi & NCR", "8447": "Delhi & NCR",
    "8448": "Delhi & NCR", "8527": "Delhi & NCR", "8585": "Delhi & NCR", "8586": "Delhi & NCR",
    "8587": "Delhi & NCR", "8588": "Delhi & NCR", "8700": "Delhi & NCR", "8743": "Delhi & NCR",
    "8744": "Delhi & NCR", "8745": "Delhi & NCR", "8750": "Delhi & NCR", "8802": "Delhi & NCR",
    "8826": "Delhi & NCR", "8860": "Delhi & NCR", "8920": "Delhi & NCR", "8929": "Delhi & NCR",
    "7011": "Delhi & NCR", "7042": "Delhi & NCR", "7053": "Delhi & NCR", "7065": "Delhi & NCR",
    "7210": "Delhi & NCR", "7289": "Delhi & NCR", "7290": "Delhi & NCR", "7291": "Delhi & NCR",
    "7292": "Delhi & NCR", "7303": "Delhi & NCR", "7428": "Delhi & NCR", "7503": "Delhi & NCR",
    "7531": "Delhi & NCR", "7532": "Delhi & NCR", "7533": "Delhi & NCR", "7827": "Delhi & NCR",
    "7834": "Delhi & NCR", "7835": "Delhi & NCR", "7836": "Delhi & NCR", "7838": "Delhi & NCR",
    "7840": "Delhi & NCR", "7982": "Delhi & NCR", "6390": "Delhi & NCR",

    # ── Mumbai ───────────────────────────────────────────────────────────
    "9820": "Mumbai", "9821": "Mumbai", "9819": "Mumbai", "9833": "Mumbai",
    "9920": "Mumbai", "9930": "Mumbai", "9869": "Mumbai", "9892": "Mumbai",
    "9967": "Mumbai", "9969": "Mumbai", "9702": "Mumbai", "9769": "Mumbai",
    "9619": "Mumbai", "9004": "Mumbai", "9029": "Mumbai", "9167": "Mumbai",
    "9223": "Mumbai", "9224": "Mumbai", "9320": "Mumbai", "9321": "Mumbai",
    "9322": "Mumbai", "9323": "Mumbai", "9324": "Mumbai", "8080": "Mumbai",
    "8082": "Mumbai", "8097": "Mumbai", "8104": "Mumbai", "8108": "Mumbai",
    "8291": "Mumbai", "8422": "Mumbai", "8424": "Mumbai", "8425": "Mumbai",
    "8433": "Mumbai", "8451": "Mumbai", "8452": "Mumbai", "8454": "Mumbai",
    "8652": "Mumbai", "8655": "Mumbai", "8657": "Mumbai", "8828": "Mumbai",
    "8879": "Mumbai", "8898": "Mumbai", "8976": "Mumbai", "7021": "Mumbai",
    "7045": "Mumbai", "7208": "Mumbai", "7304": "Mumbai", "7400": "Mumbai",
    "7506": "Mumbai", "7666": "Mumbai", "7710": "Mumbai", "7715": "Mumbai",
    "7718": "Mumbai", "7738": "Mumbai", "7875": "Mumbai", "7977": "Mumbai",

    # ── Maharashtra & Goa ───────────────────────────────────────────────
    "9822": "Maharashtra & Goa", "9823": "Maharashtra & Goa", "9850": "Maharashtra & Goa",
    "9881": "Maharashtra & Goa", "9922": "Maharashtra & Goa", "9923": "Maharashtra & Goa",
    "9762": "Maharashtra & Goa", "9763": "Maharashtra & Goa", "9764": "Maharashtra & Goa",
    "9765": "Maharashtra & Goa", "9422": "Maharashtra & Goa", "9423": "Maharashtra & Goa",
    "9604": "Maharashtra & Goa", "9623": "Maharashtra & Goa", "9637": "Maharashtra & Goa",
    "9657": "Maharashtra & Goa", "9665": "Maharashtra & Goa", "9673": "Maharashtra & Goa",
    "9689": "Maharashtra & Goa", "9011": "Maharashtra & Goa", "9028": "Maharashtra & Goa",
    "9049": "Maharashtra & Goa", "9096": "Maharashtra & Goa", "9158": "Maharashtra & Goa",
    "9175": "Maharashtra & Goa", "9225": "Maharashtra & Goa", "9226": "Maharashtra & Goa",
    "9325": "Maharashtra & Goa", "9326": "Maharashtra & Goa", "9370": "Maharashtra & Goa",
    "9371": "Maharashtra & Goa", "9372": "Maharashtra & Goa", "9373": "Maharashtra & Goa",
    "8007": "Maharashtra & Goa", "8055": "Maharashtra & Goa", "8275": "Maharashtra & Goa",
    "8308": "Maharashtra & Goa", "8378": "Maharashtra & Goa", "8380": "Maharashtra & Goa",
    "8390": "Maharashtra & Goa", "8408": "Maharashtra & Goa", "8411": "Maharashtra & Goa",
    "8446": "Maharashtra & Goa", "8483": "Maharashtra & Goa", "8484": "Maharashtra & Goa",
    "8600": "Maharashtra & Goa", "8605": "Maharashtra & Goa", "8623": "Maharashtra & Goa",
    "8624": "Maharashtra & Goa", "8625": "Maharashtra & Goa", "8698": "Maharashtra & Goa",
    "8805": "Maharashtra & Goa", "8806": "Maharashtra & Goa", "8888": "Maharashtra & Goa",
    "8956": "Maharashtra & Goa", "8975": "Maharashtra & Goa", "8983": "Maharashtra & Goa",
    "8999": "Maharashtra & Goa", "7020": "Maharashtra & Goa", "7028": "Maharashtra & Goa",

    # ── Karnataka ────────────────────────────────────────────────────────
    "9844": "Karnataka", "9845": "Karnataka", "9880": "Karnataka", "9900": "Karnataka",
    "9945": "Karnataka", "9980": "Karnataka", "9448": "Karnataka", "7019": "Karnataka",
    "9741": "Karnataka",

    # ── Kerala ───────────────────────────────────────────────────────────
    "9846": "Kerala", "9847": "Kerala", "9995": "Kerala", "9447": "Kerala", "7012": "Kerala",

    # ── Kolkata ──────────────────────────────────────────────────────────
    "9830": "Kolkata", "9831": "Kolkata", "9836": "Kolkata", "9903": "Kolkata",
    "9874": "Kolkata",

    # ── Andhra Pradesh & Telangana ───────────────────────────────────────
    "9848": "Andhra Pradesh & Telangana", "9849": "Andhra Pradesh & Telangana",
    "9866": "Andhra Pradesh & Telangana", "9948": "Andhra Pradesh & Telangana",
    "9949": "Andhra Pradesh & Telangana", "9440": "Andhra Pradesh & Telangana",
    "7013": "Andhra Pradesh & Telangana", "9553": "Andhra Pradesh & Telangana",

    # ── Madhya Pradesh & Chhattisgarh ────────────────────────────────────
    "9826": "Madhya Pradesh & Chhattisgarh", "9827": "Madhya Pradesh & Chhattisgarh",
    "9893": "Madhya Pradesh & Chhattisgarh", "9926": "Madhya Pradesh & Chhattisgarh",
    "9425": "Madhya Pradesh & Chhattisgarh",

    # ── UP East ──────────────────────────────────────────────────────────
    "9839": "UP East", "9838": "UP East", "9935": "UP East", "9936": "UP East",
    "9415": "UP East",

    # ── UP West & Uttarakhand ───────────────────────────────────────────
    "9837": "UP West & Uttarakhand", "9897": "UP West & Uttarakhand",
    "9927": "UP West & Uttarakhand", "9412": "UP West & Uttarakhand",

    # ── Bihar & Jharkhand ────────────────────────────────────────────────
    "9835": "Bihar & Jharkhand", "9834": "Bihar & Jharkhand", "9934": "Bihar & Jharkhand",
    "9431": "Bihar & Jharkhand",

    # ── Rajasthan ────────────────────────────────────────────────────────
    "9829": "Rajasthan", "9828": "Rajasthan", "9928": "Rajasthan", "9414": "Rajasthan",
    "8107": "Rajasthan",

    # ── Punjab ───────────────────────────────────────────────────────────
    "9814": "Punjab", "9815": "Punjab", "9872": "Punjab", "9914": "Punjab",
    "9417": "Punjab",

    # ── West Bengal ──────────────────────────────────────────────────────
    "9832": "West Bengal", "9932": "West Bengal", "9434": "West Bengal",

    # ── Chennai ──────────────────────────────────────────────────────────
    "9841": "Chennai", "9840": "Chennai", "9884": "Chennai", "9940": "Chennai",

    # ── Odisha ───────────────────────────────────────────────────────────
    "9861": "Odisha", "9937": "Odisha", "9437": "Odisha",

    # ── Assam ────────────────────────────────────────────────────────────
    "9864": "Assam", "9954": "Assam", "9435": "Assam",

    # ── Haryana ──────────────────────────────────────────────────────────
    "9812": "Haryana", "9896": "Haryana", "9416": "Haryana",

    # ── Himachal Pradesh ─────────────────────────────────────────────────
    "9816": "Himachal Pradesh", "9418": "Himachal Pradesh",

    # ── Jammu & Kashmir ──────────────────────────────────────────────────
    "9858": "Jammu & Kashmir", "9419": "Jammu & Kashmir",

    # ── North East ───────────────────────────────────────────────────────
    "9862": "North East", "9436": "North East",

    # ── 3-digit fallback blocks ───────────────────────────────────────────
    "638": "Tamil Nadu", "637": "Tamil Nadu", "639": "UP East",
    "636": "Karnataka", "620": "Bihar & Jharkhand", "629": "West Bengal",
    "700": "Kolkata", "701": "Delhi & NCR", "702": "Maharashtra & Goa",
    "703": "Maharashtra & Goa", "704": "Gujarat", "705": "UP West & Uttarakhand",
    "706": "Gujarat", "707": "Bihar & Jharkhand", "708": "UP East",
    "709": "Tamil Nadu", "910": "Gujarat", "915": "Tamil Nadu",
    "917": "Tamil Nadu", "922": "Gujarat", "926": "Gujarat",
}
