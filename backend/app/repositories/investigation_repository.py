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

    def create(self, *, name: str, user_id: uuid.UUID | None = None) -> Investigation:
        """Persist a new investigation and return the created row."""
        investigation = Investigation(name=name, user_id=user_id)
        self._db.add(investigation)
        self._db.commit()
        self._db.refresh(investigation)
        return investigation

    def get_by_id(self, investigation_id: uuid.UUID) -> Investigation | None:
        """Fetch a single investigation by primary key, or None if absent."""
        return self._db.get(Investigation, investigation_id)

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[Investigation], int]:
        """Return a page of investigations (most recent first) and the total count.

        When user_id is provided only investigations belonging to that user are
        returned. When None all investigations are returned (legacy behaviour).
        """
        base_stmt = select(Investigation)
        count_stmt = select(func.count()).select_from(Investigation)

        if user_id is not None:
            base_stmt = base_stmt.where(Investigation.user_id == user_id)
            count_stmt = count_stmt.where(Investigation.user_id == user_id)

        total = self._db.scalar(count_stmt) or 0

        stmt = (
            base_stmt
            .order_by(Investigation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(self._db.scalars(stmt).all())

        return items, total

    def update(self, investigation: Investigation) -> Investigation:
        """
        Persist changes to an existing investigation.

        Args:
            investigation: The investigation instance with modified attributes.

        Returns:
            The updated investigation (refreshed from the database).

        Note:
            The investigation must already be tracked by the session
            (e.g., retrieved via get_by_id). This method commits the
            changes and refreshes the instance.
        """
        self._db.commit()
        self._db.refresh(investigation)
        return investigation

    def delete(self, investigation: Investigation) -> None:
        """Delete an investigation and commit. Cascade is handled by the DB FK constraints."""
        self._db.delete(investigation)
        self._db.commit()