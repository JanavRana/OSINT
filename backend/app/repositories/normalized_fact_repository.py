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

    def exists(
        self,
        *,
        investigation_id: uuid.UUID,
        connector_name: str,
        fact_type: str,
        value: str,
    ) -> bool:
        """
        Check if a fact with the given key attributes already exists.
        
        This prevents storing duplicate facts across multiple connector runs.
        Two facts are considered duplicates if they have the same:
        - investigation_id
        - connector_name
        - fact_type
        - value
        
        Args:
            investigation_id: The investigation this fact belongs to
            connector_name: The source connector
            fact_type: The type of fact
            value: The fact value
            
        Returns:
            True if a matching fact already exists, False otherwise
        """
        from sqlalchemy import select, func

        stmt = (
            select(func.count())
            .select_from(NormalizedFact)
            .where(
                NormalizedFact.investigation_id == investigation_id,
                NormalizedFact.connector_name == connector_name,
                NormalizedFact.fact_type == fact_type,
                NormalizedFact.value == value,
            )
        )
        count = self._db.scalar(stmt)
        return count > 0

    def create_if_not_exists(
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
        Create a normalized fact only if it doesn't already exist.
        
        This is the primary method for storing facts with automatic deduplication.
        
        Args:
            investigation_id: The investigation this fact belongs to
            connector_name: The source connector
            fact_type: The type of fact
            value: The fact value
            confidence: Confidence score (0.0-1.0)
            fact_metadata: Additional metadata
            occurred_at: When the fact occurred
            
        Returns:
            The created NormalizedFact if it was new, None if it already existed
        """
        # Check if the fact already exists
        if self.exists(
            investigation_id=investigation_id,
            connector_name=connector_name,
            fact_type=fact_type,
            value=value,
        ):
            return None
        
        # Create the new fact
        return self.create(
            investigation_id=investigation_id,
            connector_name=connector_name,
            fact_type=fact_type,
            value=value,
            confidence=confidence,
            fact_metadata=fact_metadata,
            occurred_at=occurred_at,
        )

    def bulk_create_if_not_exists(
        self,
        *,
        investigation_id: uuid.UUID,
        facts_data: list[dict[str, Any]],
    ) -> tuple[list[NormalizedFact], int]:
        """
        Bulk create multiple facts with deduplication.
        
        More efficient than calling create_if_not_exists in a loop when
        storing many facts from multiple connectors.
        
        Args:
            investigation_id: The investigation these facts belong to
            facts_data: List of dicts, each containing:
                - connector_name: str
                - fact_type: str
                - value: str
                - confidence: float
                - fact_metadata: dict
                - occurred_at: datetime
                
        Returns:
            Tuple of (created_facts, skipped_count) where:
            - created_facts: List of newly created NormalizedFact instances
            - skipped_count: Number of duplicate facts that were skipped
        """
        from sqlalchemy import select

        created_facts = []
        skipped_count = 0
        
        # Build a set of existing fact keys to avoid individual queries
        # for each fact in the batch
        fact_keys = [
            (fact["connector_name"], fact["fact_type"], fact["value"])
            for fact in facts_data
        ]
        
        if fact_keys:
            stmt = (
                select(
                    NormalizedFact.connector_name,
                    NormalizedFact.fact_type,
                    NormalizedFact.value,
                )
                .where(
                    NormalizedFact.investigation_id == investigation_id,
                )
            )
            existing_keys = set(self._db.execute(stmt).all())
        else:
            existing_keys = set()
        
        # Create only facts that don't exist
        for fact_data in facts_data:
            key = (
                fact_data["connector_name"],
                fact_data["fact_type"],
                fact_data["value"],
            )
            
            if key in existing_keys:
                skipped_count += 1
                continue
            
            fact = NormalizedFact(
                investigation_id=investigation_id,
                connector_name=fact_data["connector_name"],
                fact_type=fact_data["fact_type"],
                value=fact_data["value"],
                confidence=fact_data["confidence"],
                fact_metadata=fact_data["fact_metadata"],
                occurred_at=fact_data["occurred_at"],
            )
            self._db.add(fact)
            created_facts.append(fact)
            # Add to existing_keys to handle duplicates within the batch
            existing_keys.add(key)
        
        if created_facts:
            self._db.commit()
            for fact in created_facts:
                self._db.refresh(fact)
        
        return created_facts, skipped_count
