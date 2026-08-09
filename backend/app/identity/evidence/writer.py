"""
Evidence writer for persisting facts to storage.

In production, writes to PostgreSQL normalized_facts and evidence tables.
"""

import logging
from typing import Optional

from .models import NormalizedFact

logger = logging.getLogger(__name__)


class EvidenceWriter:
    """
    Writes normalized facts and evidence to persistent storage.
    
    In production, this interfaces with PostgreSQL and Neo4j.
    For the framework, provides the interface.
    """
    
    def __init__(self):
        self._facts_written = 0
        self._facts_cache: dict[str, NormalizedFact] = {}
    
    async def write_fact(self, fact: NormalizedFact) -> bool:
        """
        Write a normalized fact to storage.
        
        Args:
            fact: Normalized fact to write
            
        Returns:
            True if successfully written
        """
        try:
            # In production:
            # 1. Insert into normalized_facts table
            # 2. Insert into evidence table
            # 3. Optionally write to Neo4j graph
            
            fact_key = f"{fact.investigation_id}:{fact.identifier_value}:{fact.fact_type}"
            self._facts_cache[fact_key] = fact
            self._facts_written += 1
            
            logger.info(
                f"Wrote fact: {fact.fact_type} for "
                f"{fact.identifier_type}/{fact.identifier_value} "
                f"(confidence={fact.confidence.value:.3f})"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to write fact: {e}", exc_info=True)
            return False
    
    async def write_batch(self, facts: list[NormalizedFact]) -> int:
        """
        Write multiple facts in a batch.
        
        Args:
            facts: List of facts to write
            
        Returns:
            Number of facts successfully written
        """
        written = 0
        for fact in facts:
            if await self.write_fact(fact):
                written += 1
        
        logger.info(f"Batch write complete: {written}/{len(facts)} facts written")
        return written
    
    def get_statistics(self) -> dict:
        """Get writer statistics."""
        return {
            "facts_written": self._facts_written,
            "facts_cached": len(self._facts_cache),
        }
    
    def clear(self) -> None:
        """Clear cache and statistics. Mainly for testing."""
        self._facts_cache.clear()
        self._facts_written = 0


# Global singleton instance
_evidence_writer: Optional[EvidenceWriter] = None


def get_evidence_writer() -> EvidenceWriter:
    """Get the global evidence writer."""
    global _evidence_writer
    if _evidence_writer is None:
        _evidence_writer = EvidenceWriter()
    return _evidence_writer


def reset_evidence_writer() -> None:
    """Reset the global writer. Mainly for testing."""
    global _evidence_writer
    if _evidence_writer:
        _evidence_writer.clear()
    _evidence_writer = None
