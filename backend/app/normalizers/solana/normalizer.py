"""
Solana OSINT normalizer.

Converts SolanaConnector raw RPC output into normalized facts.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class SolanaNormalizer(BaseNormalizer):
    """
    Normalizer for the 'solana' connector.
    """
    
    connector_name: ClassVar[str] = "solana"
    
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
                "address_type": raw_payload.get("address_type", "solana_account"),
                "valid": valid,
                "blockchain": "solana",
                "error": error,
            },
        )
        facts.append(wallet_fact)
        
        if not valid or error:
            return facts
        
        # 2. Balance fact
        balance_sol = raw_payload.get("balance_sol", 0.0)
        balance_lamports = raw_payload.get("balance_lamports", 0)
        facts.append(
            NormalizedFact(
                fact_type=FactType.GENERIC,
                value=f"{balance_sol:.6f} SOL",
                confidence=0.95,
                source_connector=self.connector_name,
                metadata={
                    "wallet_address": address,
                    "balance_sol": balance_sol,
                    "balance_lamports": balance_lamports,
                    "currency": "SOL",
                    "blockchain": "solana",
                    "data_type": "balance",
                },
            )
        )
        
        return facts
