"""
SeedIdentifier repository.

Encapsulates all direct SQLAlchemy access for the SeedIdentifier entity.
This is the only place in the codebase that should issue queries
against the `seed_identifiers` table.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seed_identifier import SeedIdentifier


class SeedIdentifierRepository:
    """Data-access layer for the SeedIdentifier entity."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        investigation_id: uuid.UUID,
        value: str,
        identifier_type: str,
    ) -> SeedIdentifier:
        """Persist a new seed identifier and return the created row."""
        seed = SeedIdentifier(
            investigation_id=investigation_id,
            value=value,
            type=identifier_type,
        )
        self._db.add(seed)
        self._db.commit()
        self._db.refresh(seed)
        return seed

    def get_primary_by_investigation(
        self, investigation_id: uuid.UUID
    ) -> Optional[SeedIdentifier]:
        """
        Return the primary (first-created) seed identifier for an investigation.

        Returns None if no seed has been saved yet (e.g., legacy investigations
        created before this feature existed).
        """
        stmt = (
            select(SeedIdentifier)
            .where(SeedIdentifier.investigation_id == investigation_id)
            .order_by(SeedIdentifier.created_at.asc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()
