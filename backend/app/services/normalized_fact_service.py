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