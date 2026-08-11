"""
Bitcoin OSINT connector using Blockstream Esplora API.

This connector:
1. Subclasses BaseConnector and registers via @registry.register
2. Accepts only WALLET_ADDRESS identifiers
3. Uses the public Blockstream Esplora API (no authentication required)
4. Validates Bitcoin addresses (legacy, P2SH, Bech32)
5. Retrieves public blockchain data (balance, transactions, UTXOs)
6. Returns RAW response for downstream normalization
7. Does NOT normalize data itself
8. Does NOT access database
9. Does NOT handle private keys or wallet recovery

Blockstream Esplora API endpoints used:
- GET /address/{address} - Address stats (balance, tx count)
- GET /address/{address}/txs - Transaction history
- GET /address/{address}/utxo - Unspent transaction outputs
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional

import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import validate_bitcoin_address, get_address_type


# Configurable limits to prevent excessive data retrieval
MAX_TRANSACTIONS = 25  # Limit recent transactions to prevent huge responses
UTXO_LIMIT = 100  # Limit UTXOs returned


@registry.register
class BitcoinConnector(BaseConnector):
    """
    Bitcoin blockchain OSINT connector.
    
    Retrieves public blockchain data for Bitcoin addresses using the
    Blockstream Esplora API.
    
    Produces a structured dict containing:
    - Address validation status and type
    - Confirmed and unconfirmed balance (in satoshis)
    - Transaction count (sent/received)
    - Total received and spent
    - Recent transaction history (limited)
    - UTXOs (unspent outputs)
    - First and last activity timestamps
    """

    name: ClassVar[str] = "bitcoin"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.WALLET_ADDRESS}
    )
    # Bitcoin API calls can be slow, especially for active addresses
    timeout_seconds: ClassVar[float] = 30.0
    
    # Blockstream Esplora API base URL (public, no auth required)
    _base_url: ClassVar[str] = "https://blockstream.info/api"

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Fetch Bitcoin address data from Blockstream Esplora API.
        
        Args:
            identifier: A WALLET_ADDRESS identifier containing a Bitcoin address
            
        Returns:
            A JSON-serializable dict with all extracted blockchain data.
            Always returns a dict (never raises) - errors are captured in
            the 'error' field.
        """
        address = identifier.value.strip()
        
        result: Dict[str, Any] = {
            "address": address,
            "valid": False,
            "address_type": None,
            "balance_confirmed_satoshi": 0,
            "balance_unconfirmed_satoshi": 0,
            "tx_count": 0,
            "total_received_satoshi": 0,
            "total_sent_satoshi": 0,
            "transactions": [],
            "utxos": [],
            "first_seen": None,
            "last_seen": None,
            "error": None,
        }
        
        # ── Validate address ───────────────────────────────────────────────
        if not validate_bitcoin_address(address):
            result["error"] = "Invalid Bitcoin address format"
            return result
        
        result["valid"] = True
        result["address_type"] = get_address_type(address)
        
        # ── Fetch address stats ────────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # Get address stats (balance, tx count)
                stats = await self._get_address_stats(client, address)
                if stats:
                    result["balance_confirmed_satoshi"] = stats.get(
                        "chain_stats", {}
                    ).get("funded_txo_sum", 0) - stats.get(
                        "chain_stats", {}
                    ).get("spent_txo_sum", 0)
                    
                    result["balance_unconfirmed_satoshi"] = stats.get(
                        "mempool_stats", {}
                    ).get("funded_txo_sum", 0) - stats.get(
                        "mempool_stats", {}
                    ).get("spent_txo_sum", 0)
                    
                    result["tx_count"] = stats.get("chain_stats", {}).get("tx_count", 0)
                    result["total_received_satoshi"] = stats.get(
                        "chain_stats", {}
                    ).get("funded_txo_sum", 0)
                    result["total_sent_satoshi"] = stats.get(
                        "chain_stats", {}
                    ).get("spent_txo_sum", 0)
                
                # Get recent transactions (limited to prevent excessive data)
                txs = await self._get_address_transactions(client, address)
                if txs:
                    result["transactions"] = txs[:MAX_TRANSACTIONS]
                    
                    # Determine first and last seen from transactions
                    if txs:
                        # Transactions are returned newest first
                        result["last_seen"] = txs[0].get("status", {}).get("block_time")
                        result["first_seen"] = txs[-1].get("status", {}).get("block_time")
                
                # Get UTXOs
                utxos = await self._get_address_utxos(client, address)
                if utxos:
                    result["utxos"] = utxos[:UTXO_LIMIT]
        
        except httpx.TimeoutException:
            result["error"] = "Blockstream API request timed out"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                result["error"] = "Rate limited by Blockstream API (HTTP 429)"
            elif 500 <= e.response.status_code < 600:
                result["error"] = f"Blockstream API server error (HTTP {e.response.status_code})"
            else:
                result["error"] = f"HTTP error {e.response.status_code}: {str(e)}"
        except httpx.RequestError as e:
            result["error"] = f"Network error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    async def _get_address_stats(
        self, client: httpx.AsyncClient, address: str
    ) -> Optional[Dict[str, Any]]:
        """Get address statistics (balance, tx count)."""
        try:
            response = await client.get(f"{self._base_url}/address/{address}")
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    async def _get_address_transactions(
        self, client: httpx.AsyncClient, address: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get transaction history for an address."""
        try:
            response = await client.get(f"{self._base_url}/address/{address}/txs")
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    async def _get_address_utxos(
        self, client: httpx.AsyncClient, address: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get unspent transaction outputs (UTXOs) for an address."""
        try:
            response = await client.get(f"{self._base_url}/address/{address}/utxo")
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
