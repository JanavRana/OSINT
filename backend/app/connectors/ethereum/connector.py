"""
Ethereum (EVM) OSINT connector using public RPC node.

This connector:
1. Subclasses BaseConnector and registers via @registry.register
2. Accepts WALLET_ADDRESS identifiers (EVM format 0x...)
3. Uses public Ethereum RPC endpoints (no API key required)
4. Retrieves confirmed ETH balance and transaction count
5. Returns RAW response for downstream normalization
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, FrozenSet, Optional

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import validate_ethereum_address, get_address_type


@registry.register
class EthereumConnector(BaseConnector):
    """
    Ethereum blockchain OSINT connector.
    """

    name: ClassVar[str] = "ethereum"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.WALLET_ADDRESS}
    )
    timeout_seconds: ClassVar[float] = 15.0
    
    # Public Ethereum Mainnet RPC node
    _rpc_url: ClassVar[str] = "https://ethereum-rpc.publicnode.com"

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Fetch Ethereum address stats from Public JSON-RPC Node.
        """
        address = identifier.value.strip()
        
        result: Dict[str, Any] = {
            "address": address,
            "valid": False,
            "blockchain": "ethereum",
            "address_type": None,
            "balance_wei": 0,
            "balance_eth": 0.0,
            "tx_count": 0,
            "error": None,
        }
        
        if not validate_ethereum_address(address):
            result["error"] = "Invalid Ethereum address format"
            return result
        
        result["valid"] = True
        result["address_type"] = get_address_type(address)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # 1. Fetch balance (eth_getBalance)
                balance_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1,
                }
                res_bal = await client.post(self._rpc_url, json=balance_payload)
                res_bal.raise_for_status()
                bal_data = res_bal.json()
                
                if "result" in bal_data:
                    wei_hex = bal_data["result"]
                    wei_val = int(wei_hex, 16)
                    result["balance_wei"] = wei_val
                    result["balance_eth"] = wei_val / 1e18
                
                # 2. Fetch transaction count (eth_getTransactionCount)
                tx_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionCount",
                    "params": [address, "latest"],
                    "id": 2,
                }
                res_tx = await client.post(self._rpc_url, json=tx_payload)
                res_tx.raise_for_status()
                tx_data = res_tx.json()
                
                if "result" in tx_data:
                    tx_hex = tx_data["result"]
                    result["tx_count"] = int(tx_hex, 16)
                    
        except httpx.TimeoutException:
            result["error"] = "Ethereum RPC request timed out"
        except httpx.HTTPStatusError as e:
            result["error"] = f"HTTP error {e.response.status_code}: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
