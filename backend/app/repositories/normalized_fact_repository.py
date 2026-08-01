"""
NormalizedFact repository.

Encapsulates all direct SQLAlchemy access for the NormalizedFact entity.
This is the only place in the codebase that should issue queries
against the `normalized_facts` table.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.normalized_fact import NormalizedFact


class NormalizedFactRepository:
    """Data-access layer for the NormalizedFact entity."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
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
        """Persist a new normalized fact and return the created row."""
        fact = NormalizedFact(
            investigation_id=investigation_id,
            connector_name=connector_name,
            fact_type=fact_type,
            value=value,
            confidence=confidence,
            fact_metadata=fact_metadata,
            occurred_at=occurred_at,
        )
        self._db.add(fact)
        self._db.commit()
        self._db.refresh(fact)
        return fact

    def list_by_investigation(
        self, investigation_id: uuid.UUID
    ) -> list[NormalizedFact]:
        """Return all normalized facts for a given investigation."""
        from sqlalchemy import select

        stmt = (
            select(NormalizedFact)
            .where(NormalizedFact.investigation_id == investigation_id)
            .order_by(NormalizedFact.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())
