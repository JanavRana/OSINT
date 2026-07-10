"""
Investigation service.

Holds the business logic for the Investigation resource, sitting between
the API router and the repository (data-access) layer. For Sprint 2 this
logic is intentionally thin (create / retrieve / list), but keeping the
layer in place now means future rules — e.g. validating identifiers
before allowing creation, or enforcing status transitions once
orchestration (M1) exists — have an obvious home without reshaping the
router or repository.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.repositories.investigation_repository import InvestigationRepository
from app.services.exceptions import NotFoundError


class InvestigationService:
    """Business logic for creating and retrieving investigations."""

    def __init__(self, db: Session) -> None:
        self._repo = InvestigationRepository(db)

    def create_investigation(self, *, name: str) -> Investigation:
        """Create a new investigation.

        Sprint 2 scope: just persists the record with default status.
        Future sprints may extend this to accept initial identifiers
        (FR1.3) and kick off orchestration (M1) — neither is implemented
        here.
        """
        return self._repo.create(name=name)

    def get_investigation(self, investigation_id: uuid.UUID) -> Investigation:
        """Fetch a single investigation, raising NotFoundError if absent."""
        investigation = self._repo.get_by_id(investigation_id)
        if investigation is None:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        return investigation

    def list_investigations(
        self, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Investigation], int]:
        """Return a page of investigations and the total count available."""
        return self._repo.list(skip=skip, limit=limit)