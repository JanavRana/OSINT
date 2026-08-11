"""
Solana OSINT connector using public RPC node.

This connector:
1. Subclasses BaseConnector and registers via @registry.register
2. Accepts WALLET_ADDRESS identifiers (Solana Base58 format)
3. Uses public Solana Mainnet RPC node (no API key required)
4. Retrieves confirmed SOL balance (converted from lamports)
5. Returns RAW response for downstream normalization
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, FrozenSet

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import validate_solana_address, get_address_type


@registry.register
class SolanaConnector(BaseConnector):
    """
    Solana blockchain OSINT connector.
    """

    name: ClassVar[str] = "solana"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.WALLET_ADDRESS}
    )
    timeout_seconds: ClassVar[float] = 15.0
    
    # Public Solana Mainnet RPC node
    _rpc_url: ClassVar[str] = "https://api.mainnet-beta.solana.com"

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Fetch Solana address stats from Public JSON-RPC Node.
        """
        address = identifier.value.strip()
        
        result: Dict[str, Any] = {
            "address": address,
            "valid": False,
            "blockchain": "solana",
            "address_type": None,
            "balance_lamports": 0,
            "balance_sol": 0.0,
            "error": None,
        }
        
        if not validate_solana_address(address):
            result["error"] = "Invalid Solana address format"
            return result
        
        result["valid"] = True
        result["address_type"] = get_address_type(address)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # Fetch balance (getBalance)
                payload = {
                    "jsonrpc": "2.0",
                    "method": "getBalance",
                    "params": [address],
                    "id": 1,
                }
                response = await client.post(self._rpc_url, json=payload)
                response.raise_for_status()
                res_data = response.json()
                
                if "result" in res_data and isinstance(res_data["result"], dict):
                    lamports = res_data["result"].get("value", 0)
                    result["balance_lamports"] = lamports
                    result["balance_sol"] = lamports / 1e9
                elif "error" in res_data:
                    result["error"] = f"RPC error: {res_data['error'].get('message', 'Unknown')}"
                    
        except httpx.TimeoutException:
            result["error"] = "Solana RPC request timed out"
        except httpx.HTTPStatusError as e:
            result["error"] = f"HTTP error {e.response.status_code}: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
