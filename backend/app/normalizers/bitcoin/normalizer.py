"""
Bitcoin OSINT normalizer.

Converts the BitcoinConnector's raw blockchain data into normalized facts
following the shared internal schema (M3, Section 11.3 of MASTER_DESIGN.md).

Confidence assignments:

WALLET_ADDRESS (valid Bitcoin address)          → 1.00
FINANCIAL (balance - confirmed blockchain data) → 0.95
FINANCIAL (balance - unconfirmed)               → 0.70
GENERIC (transaction count)                     → 0.95
FINANCIAL (total received/sent)                 → 0.95
GENERIC (first/last seen timestamps)            → 0.95
GENERIC (UTXO data)                             → 0.90

IMPORTANT: This normalizer does NOT claim wallet ownership by any person.
All facts are blockchain data only. Any attribution would require
additional sources and correlation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class BitcoinNormalizer(BaseNormalizer):
    """
    Normalizer for the 'bitcoin' connector's raw payload.
    
    Extracts NormalizedFact instances from the structured dict produced
    by BitcoinConnector.fetch():
    
    - WALLET_ADDRESS fact: the Bitcoin address itself
    - FINANCIAL facts: balances, total received/sent
    - GENERIC facts: transaction count, UTXOs, activity timestamps
    
    If the connector reported an error or invalid address, minimal facts
    are produced to maintain audit trail.
    """
    
    connector_name: ClassVar[str] = "bitcoin"
    
    # Confidence constants
    _CONF_ADDRESS_VALID: float = 1.00        # Valid Bitcoin address format
    _CONF_BALANCE_CONFIRMED: float = 0.95    # Confirmed blockchain data
    _CONF_BALANCE_UNCONFIRMED: float = 0.70  # Unconfirmed (mempool) data
    _CONF_TX_DATA: float = 0.95              # Transaction count and totals
    _CONF_TIMESTAMPS: float = 0.95           # Blockchain timestamps
    _CONF_UTXO: float = 0.90                 # UTXO data
    _CONF_ADDRESS_INVALID: float = 0.10      # Invalid address (audit only)
    
    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert BitcoinConnector's raw dict into normalized facts.
        
        Args:
            raw_payload: The dict returned by BitcoinConnector.fetch()
            
        Returns:
            A list of NormalizedFact instances. Never empty - always at
            least one WALLET_ADDRESS fact (even on error, to preserve audit trail).
            
        Raises:
            NormalizationError: If raw_payload is not a dict
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )
        
        facts: List[NormalizedFact] = []
        
        error = raw_payload.get("error")
        valid = raw_payload.get("valid", False)
        address = raw_payload.get("address", "")
        
        # ── 1. Primary WALLET_ADDRESS fact ────────────────────────────────
        wallet_fact = self._build_wallet_fact(raw_payload, valid, error)
        facts.append(wallet_fact)
        
        # Stop here if address is invalid or there was an error
        if not valid or error:
            return facts
        
        # ── 2. Balance facts ───────────────────────────────────────────────
        balance_confirmed = raw_payload.get("balance_confirmed_satoshi", 0)
        balance_unconfirmed = raw_payload.get("balance_unconfirmed_satoshi", 0)
        
        if balance_confirmed > 0 or balance_unconfirmed > 0:
            facts.append(self._build_balance_fact(
                address,
                balance_confirmed,
                balance_unconfirmed
            ))
        
        # ── 3. Transaction count ───────────────────────────────────────────
        tx_count = raw_payload.get("tx_count", 0)
        if tx_count > 0:
            facts.append(self._build_tx_count_fact(address, tx_count))
        
        # ── 4. Total received/sent ─────────────────────────────────────────
        total_received = raw_payload.get("total_received_satoshi", 0)
        total_sent = raw_payload.get("total_sent_satoshi", 0)
        
        if total_received > 0 or total_sent > 0:
            facts.append(self._build_totals_fact(
                address,
                total_received,
                total_sent
            ))
        
        # ── 5. Activity timestamps ─────────────────────────────────────────
        first_seen = raw_payload.get("first_seen")
        last_seen = raw_payload.get("last_seen")
        
        if first_seen:
            facts.append(self._build_timestamp_fact(
                address,
                "first_activity",
                first_seen
            ))
        
        if last_seen:
            facts.append(self._build_timestamp_fact(
                address,
                "last_activity",
                last_seen
            ))
        
        # ── 6. Transaction history (for timeline/graph) ───────────────────
        transactions = raw_payload.get("transactions", [])
        for tx in transactions:
            tx_fact = self._build_transaction_fact(address, tx)
            if tx_fact:
                facts.append(tx_fact)
        
        # ── 7. UTXO data ───────────────────────────────────────────────────
        utxos = raw_payload.get("utxos", [])
        if utxos:
            facts.append(self._build_utxo_fact(address, utxos))
        
        return facts
    
    def _build_wallet_fact(
        self,
        raw_payload: Dict[str, Any],
        valid: bool,
        error: Optional[str]
    ) -> NormalizedFact:
        """Build the primary WALLET_ADDRESS fact."""
        address = raw_payload.get("address", "")
        address_type = raw_payload.get("address_type")
        
        confidence = self._CONF_ADDRESS_VALID if valid else self._CONF_ADDRESS_INVALID
        
        metadata = {
            "address_type": address_type,
            "valid": valid,
            "blockchain": "bitcoin",
        }
        
        if error:
            metadata["error"] = error
        
        return NormalizedFact(
            fact_type=FactType.WALLET_ADDRESS,
            value=address,
            confidence=confidence,
            source_connector=self.connector_name,
            metadata=metadata,
        )
    
    def _build_balance_fact(
        self,
        address: str,
        confirmed: int,
        unconfirmed: int
    ) -> NormalizedFact:
        """Build balance fact with confirmed and unconfirmed amounts."""
        # Convert satoshis to BTC for display
        confirmed_btc = confirmed / 100_000_000
        unconfirmed_btc = unconfirmed / 100_000_000
        
        # Use confirmed balance confidence if unconfirmed is zero
        confidence = self._CONF_BALANCE_CONFIRMED if unconfirmed == 0 else self._CONF_BALANCE_UNCONFIRMED
        
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=f"{confirmed_btc:.8f} BTC",
            confidence=confidence,
            source_connector=self.connector_name,
            metadata={
                "wallet_address": address,
                "balance_confirmed_satoshi": confirmed,
                "balance_unconfirmed_satoshi": unconfirmed,
                "balance_confirmed_btc": confirmed_btc,
                "balance_unconfirmed_btc": unconfirmed_btc,
                "currency": "BTC",
                "blockchain": "bitcoin",
                "data_type": "balance",
            },
        )
    
    def _build_tx_count_fact(
        self,
        address: str,
        tx_count: int
    ) -> NormalizedFact:
        """Build transaction count fact."""
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=f"{tx_count} transactions",
            confidence=self._CONF_TX_DATA,
            source_connector=self.connector_name,
            metadata={
                "wallet_address": address,
                "transaction_count": tx_count,
                "data_type": "transaction_count",
                "blockchain": "bitcoin",
            },
        )
    
    def _build_totals_fact(
        self,
        address: str,
        received: int,
        sent: int
    ) -> NormalizedFact:
        """Build total received/sent fact."""
        received_btc = received / 100_000_000
        sent_btc = sent / 100_000_000
        
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=f"Received {received_btc:.8f} BTC, Sent {sent_btc:.8f} BTC",
            confidence=self._CONF_TX_DATA,
            source_connector=self.connector_name,
            metadata={
                "wallet_address": address,
                "total_received_satoshi": received,
                "total_sent_satoshi": sent,
                "total_received_btc": received_btc,
                "total_sent_btc": sent_btc,
                "currency": "BTC",
                "blockchain": "bitcoin",
                "data_type": "totals",
            },
        )
    
    def _build_timestamp_fact(
        self,
        address: str,
        activity_type: str,
        timestamp: int
    ) -> NormalizedFact:
        """Build activity timestamp fact."""
        dt = datetime.fromtimestamp(timestamp)
        
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=dt.isoformat(),
            confidence=self._CONF_TIMESTAMPS,
            source_connector=self.connector_name,
            occurred_at=dt,
            metadata={
                "wallet_address": address,
                "activity_type": activity_type,
                "timestamp": timestamp,
                "data_type": "timestamp",
                "blockchain": "bitcoin",
            },
        )
    
    def _build_transaction_fact(
        self,
        address: str,
        tx: Dict[str, Any]
    ) -> Optional[NormalizedFact]:
        """Build transaction fact for timeline/graph."""
        try:
            txid = tx.get("txid")
            status = tx.get("status", {})
            block_time = status.get("block_time")
            
            if not txid or not block_time:
                return None
            
            # Determine if this is incoming or outgoing
            vin = tx.get("vin", [])
            vout = tx.get("vout", [])
            
            # Simple heuristic: check if address appears in inputs or outputs
            is_sender = any(
                inp.get("prevout", {}).get("scriptpubkey_address") == address
                for inp in vin
            )
            
            is_receiver = any(
                out.get("scriptpubkey_address") == address
                for out in vout
            )
            
            # Calculate amount involved
            amount = 0
            if is_receiver:
                # Sum outputs to this address
                amount = sum(
                    out.get("value", 0)
                    for out in vout
                    if out.get("scriptpubkey_address") == address
                )
            elif is_sender:
                # Sum inputs from this address
                amount = sum(
                    inp.get("prevout", {}).get("value", 0)
                    for inp in vin
                    if inp.get("prevout", {}).get("scriptpubkey_address") == address
                )
            
            amount_btc = amount / 100_000_000
            
            direction = "received" if is_receiver else "sent" if is_sender else "unknown"
            
            dt = datetime.fromtimestamp(block_time)
            
            # Extract related addresses for graph relationships
            related_addresses = []
            if is_receiver:
                # Sender addresses
                related_addresses = [
                    inp.get("prevout", {}).get("scriptpubkey_address")
                    for inp in vin
                    if inp.get("prevout", {}).get("scriptpubkey_address")
                ]
            elif is_sender:
                # Receiver addresses
                related_addresses = [
                    out.get("scriptpubkey_address")
                    for out in vout
                    if out.get("scriptpubkey_address") and out.get("scriptpubkey_address") != address
                ]
            
            # Remove None values
            related_addresses = [addr for addr in related_addresses if addr]
            
            return NormalizedFact(
                fact_type=FactType.GENERIC,
                value=f"Transaction {direction}: {amount_btc:.8f} BTC",
                confidence=self._CONF_TX_DATA,
                source_connector=self.connector_name,
                occurred_at=dt,
                metadata={
                    "wallet_address": address,
                    "transaction_id": txid,
                    "direction": direction,
                    "amount_satoshi": amount,
                    "amount_btc": amount_btc,
                    "block_time": block_time,
                    "related_addresses": related_addresses,
                    "data_type": "transaction",
                    "blockchain": "bitcoin",
                },
            )
        except Exception:
            # Skip malformed transactions
            return None
    
    def _build_utxo_fact(
        self,
        address: str,
        utxos: List[Dict[str, Any]]
    ) -> NormalizedFact:
        """Build UTXO summary fact."""
        total_utxo_value = sum(utxo.get("value", 0) for utxo in utxos)
        total_btc = total_utxo_value / 100_000_000
        
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=f"{len(utxos)} UTXOs worth {total_btc:.8f} BTC",
            confidence=self._CONF_UTXO,
            source_connector=self.connector_name,
            metadata={
                "wallet_address": address,
                "utxo_count": len(utxos),
                "total_utxo_value_satoshi": total_utxo_value,
                "total_utxo_value_btc": total_btc,
                "currency": "BTC",
                "data_type": "utxo",
                "blockchain": "bitcoin",
            },
        )
