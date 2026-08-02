from __future__ import annotations

from typing import ClassVar, FrozenSet

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType


@registry.register
class RdapConnector(BaseConnector):
    name: ClassVar[str] = "rdap"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.DOMAIN}
    )
    timeout_seconds: ClassVar[float] = 20.0

    async def fetch(self, identifier: Identifier) -> dict:
        domain = identifier.value.lower()
        
        rdap_bootstrap_url = f"https://rdap.org/domain/{domain}"
        
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(rdap_bootstrap_url)
            response.raise_for_status()
            return response.json()
