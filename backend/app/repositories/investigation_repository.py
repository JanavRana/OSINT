"""
Investigation repository.

Encapsulates all direct SQLAlchemy access for the Investigation entity.
This is the only place in the codebase that should issue queries
against the `investigations` table — the service layer (and everything
above it) talks to investigations only through this class, in line with
M9's role as the single persistence boundary (MASTER_DESIGN.md Section
11.9 / NFR2).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation


class InvestigationRepository:
    """Data-access layer for the Investigation entity."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, *, name: str) -> Investigation:
        """Persist a new investigation and return the created row."""
        investigation = Investigation(name=name)
        self._db.add(investigation)
        self._db.commit()
        self._db.refresh(investigation)
        return investigation

    def get_by_id(self, investigation_id: uuid.UUID) -> Investigation | None:
        """Fetch a single investigation by primary key, or None if absent."""
        return self._db.get(Investigation, investigation_id)

    def list(self, *, skip: int = 0, limit: int = 100) -> tuple[list[Investigation], int]:
        """Return a page of investigations (most recent first) and the total count."""
        total = self._db.scalar(select(func.count()).select_from(Investigation)) or 0

        stmt = (
            select(Investigation)
            .order_by(Investigation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(self._db.scalars(stmt).all())

        return items, total