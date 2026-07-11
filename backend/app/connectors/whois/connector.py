"""
connectors/whois/connector.py

WHOIS connector implementation using the python-whois library.

This connector:
    1. Subclasses BaseConnector
    2. Registers itself automatically via the @registry.register decorator
    3. Accepts only DOMAIN identifiers
    4. Performs WHOIS lookups using the python-whois library
    5. Returns RAW responses without normalization
    6. Does NOT store data, access database, or call FastAPI
"""

from __future__ import annotations

from typing import ClassVar, FrozenSet

import whois

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType


@registry.register
class WhoisConnector(BaseConnector):
    """
    WHOIS lookup connector for domain identifiers.

    Uses the python-whois library to perform WHOIS queries against domain
    names. Returns the raw WHOIS data structure as-is for downstream
    normalization (M3).
    """

    name: ClassVar[str] = "whois"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.DOMAIN}
    )
    timeout_seconds: ClassVar[float] = 30.0  # WHOIS can be slow

    async def fetch(self, identifier: Identifier) -> dict:
        """
        Perform WHOIS lookup for the given domain identifier.

        Args:
            identifier: A domain identifier (e.g., value="example.com")

        Returns:
            A dictionary containing the raw WHOIS response data from the
            python-whois library. The structure is determined by the
            library and may vary slightly by TLD and registrar, but
            typically includes:
                - domain_name: str or list of domain names
                - registrar: str
                - creation_date: datetime or list of datetimes
                - expiration_date: datetime or list of datetimes
                - updated_date: datetime or list of datetimes
                - name_servers: list of nameservers
                - status: list of status strings
                - emails: list of email addresses
                - name: registrant name
                - org: registrant organization
                - address: registrant address
                - city: registrant city
                - state: registrant state
                - zipcode: registrant zipcode
                - country: registrant country

        Raises:
            whois.parser.PywhoisError: If the domain doesn't exist or
                WHOIS query fails (caught by BaseConnector.run())
            Exception: Any other error during lookup
        """
        # python-whois is synchronous, so we run it directly
        # The library handles the WHOIS protocol lookup internally
        whois_data = whois.whois(identifier.value)

        # Convert the WhoisEntry object to a dictionary for consistent handling
        # The parser module provides this as a dict-like object
        if hasattr(whois_data, "__dict__"):
            raw_dict = whois_data.__dict__.copy()
        else:
            # Fallback if the library returns a plain dict
            raw_dict = dict(whois_data) if whois_data else {}

        return raw_dict
