"""
NormalizedFact service.

Business-logic layer for NormalizedFact persistence.

Coordinates persistence operations while keeping higher layers
independent from the repository implementation.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.normalized_fact import NormalizedFact
from app.repositories.normalized_fact_repository import (
    NormalizedFactRepository,
)


class NormalizedFactService:
    """Business logic for normalized fact persistence."""

    def __init__(self, db: Session) -> None:
        self._repository = NormalizedFactRepository(db)

    def create_fact(
        self,
        *,
        investigation_id: uuid.UUID,
        connector_name: str,
        fact_type: str,
        value: str,
        confidence: float,
        fact_metadata: dict[str, Any],
        occurred_at: datetime,
    ) -> NormalizedFact:
        """Create and persist a normalized fact."""

        return self._repository.create(
            investigation_id=investigation_id,
            connector_name=connector_name,
            fact_type=fact_type,
            value=value,
            confidence=confidence,
            fact_metadata=fact_metadata,
            occurred_at=occurred_at,
        )

    def create_fact_if_not_exists(
        self,
        *,
        investigation_id: uuid.UUID,
        connector_name: str,
        fact_type: str,
        value: str,
        confidence: float,
        fact_metadata: dict[str, Any],
        occurred_at: datetime,
    ) -> NormalizedFact | None:
        """
        Create and persist a normalized fact only if it doesn't already exist.
        
        This prevents duplicate facts across multiple connector runs.
        
        Returns:
            The created NormalizedFact if it was new, None if it already existed
        """
        return self._repository.create_if_not_exists(
            investigation_id=investigation_id,
            connector_name=connector_name,
            fact_type=fact_type,
            value=value,
            confidence=confidence,
            fact_metadata=fact_metadata,
            occurred_at=occurred_at,
        )

    def bulk_create_facts_if_not_exists(
        self,
        *,
        investigation_id: uuid.UUID,
        facts_data: list[dict[str, Any]],
    ) -> tuple[list[NormalizedFact], int]:
        """
        Bulk create multiple facts with deduplication.
        
        Args:
            investigation_id: The investigation these facts belong to
            facts_data: List of dicts containing fact data
                
        Returns:
            Tuple of (created_facts, skipped_count)
        """
        return self._repository.bulk_create_if_not_exists(
            investigation_id=investigation_id,
            facts_data=facts_data,
        )