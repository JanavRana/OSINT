"""
normalizers/reverse_dns/normalizer.py

Reverse DNS normalizer implementation that converts reverse DNS results to normalized facts.

This normalizer:
    1. Subclasses BaseNormalizer
    2. Registers itself automatically via the @normalizer_registry.register decorator
    3. Handles raw reverse DNS data from the Reverse DNS connector
    4. Extracts hostnames from PTR records
    5. Produces NormalizedFact objects for downstream processing
"""

from __future__ import annotations

from typing import ClassVar, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizedFact


@normalizer_registry.register
class ReverseDnsNormalizer(BaseNormalizer):
    """
    Normalizer for Reverse DNS connector output.

    Converts reverse DNS PTR records into normalized facts,
    creating domain facts for each hostname associated with an IP address.
    """

    connector_name: ClassVar[str] = "reverse_dns"

    def normalize(self, raw_payload: dict) -> List[NormalizedFact]:
        """
        Extract normalized facts from reverse DNS results.

        Args:
            raw_payload: Raw reverse DNS data from the Reverse DNS connector
                        containing 'ip_address' and 'hostnames' keys

        Returns:
            List of NormalizedFact objects extracted from the reverse DNS data
        """
        facts: List[NormalizedFact] = []

        if not isinstance(raw_payload, dict):
            return facts

        ip_address = raw_payload.get("ip_address")
        hostnames = raw_payload.get("hostnames", [])

        if not isinstance(hostnames, list):
            return facts

        # Extract each hostname as a domain fact
        for hostname in hostnames:
            if isinstance(hostname, str) and hostname.strip():
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.DOMAIN,
                        value=hostname.strip().lower(),
                        source_connector=self.connector_name,
                        confidence=0.90,
                        metadata={
                            "record_type": "PTR",
                            "ip_address": ip_address,
                            "reverse_dns": True,
                        },
                    )
                )

        return facts
