"""
Ethereum OSINT normalizer.

Converts EthereumConnector raw RPC output into normalized facts.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class EthereumNormalizer(BaseNormalizer):
    """
    Normalizer for the 'ethereum' connector.
    """
    
    connector_name: ClassVar[str] = "ethereum"
    
    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )
        
        facts: List[NormalizedFact] = []
        
        error = raw_payload.get("error")
        valid = raw_payload.get("valid", False)
        address = raw_payload.get("address", "")
        
        # 1. Primary WALLET_ADDRESS fact
        wallet_fact = NormalizedFact(
            fact_type=FactType.WALLET_ADDRESS,
            value=address,
            confidence=1.00 if valid else 0.10,
            source_connector=self.connector_name,
            metadata={
                "address_type": raw_payload.get("address_type", "evm_account"),
                "valid": valid,
                "blockchain": "ethereum",
                "error": error,
            },
        )
        facts.append(wallet_fact)
        
        if not valid or error:
            return facts
        
        # 2. Balance fact
        balance_eth = raw_payload.get("balance_eth", 0.0)
        balance_wei = raw_payload.get("balance_wei", 0)
        facts.append(
            NormalizedFact(
                fact_type=FactType.GENERIC,
                value=f"{balance_eth:.6f} ETH",
                confidence=0.95,
                source_connector=self.connector_name,
                metadata={
                    "wallet_address": address,
                    "balance_eth": balance_eth,
                    "balance_wei": balance_wei,
                    "currency": "ETH",
                    "blockchain": "ethereum",
                    "data_type": "balance",
                },
            )
        )
        
        # 3. Transaction count fact
        tx_count = raw_payload.get("tx_count", 0)
        facts.append(
            NormalizedFact(
                fact_type=FactType.GENERIC,
                value=f"{tx_count} transactions",
                confidence=0.95,
                source_connector=self.connector_name,
                metadata={
                    "wallet_address": address,
                    "transaction_count": tx_count,
                    "data_type": "transaction_count",
                    "blockchain": "ethereum",
                },
            )
        )
        
        return facts
