"""
Investigation service.

Holds the business logic for the Investigation resource, sitting between
the API router and the repository (data-access) layer. For Sprint 2 this
logic is intentionally thin (create / retrieve / list), but keeping the
layer in place now means future rules — e.g. validating identifiers
before allowing creation, or enforcing status transitions once
orchestration (M1) exists — have an obvious home without reshaping the
router or repository.

Sprint 3 extension: adds connector execution orchestration via
ConnectorExecutionService.
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.connectors.types import Identifier, RawResponseEnvelope
from app.models.investigation import Investigation, InvestigationStatus
from app.repositories.investigation_repository import InvestigationRepository
from app.services.connector_execution_service import ConnectorExecutionService
from app.services.exceptions import NotFoundError


class InvestigationService:
    """Business logic for creating and retrieving investigations."""

    def __init__(
        self,
        db: Session,
        connector_execution_service: ConnectorExecutionService | None = None,
    ) -> None:
        self._repo = InvestigationRepository(db)
        self._connector_service = (
            connector_execution_service or ConnectorExecutionService()
        )

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

    async def execute_investigation(
        self, investigation_id: uuid.UUID, identifier: Identifier
    ) -> List[RawResponseEnvelope]:
        """
        Execute registered connectors for a given investigation and identifier.
        
        Sprint 3 scope: runs connectors synchronously and returns raw
        responses. Does NOT normalize, correlate, or persist results —
        those responsibilities belong to future sprints (M3, M4, M9
        extensions).
        
        Args:
            investigation_id: The investigation to execute connectors for.
            identifier: The identifier to investigate.
        
        Returns:
            List of RawResponseEnvelope containing raw connector responses.
        
        Raises:
            NotFoundError: If the investigation does not exist.
        
        Note:
            The investigation's status is updated to RUNNING before
            execution begins. In a future sprint, status should transition
            to COMPLETED/FAILED after execution, and results should be
            persisted. For Sprint 3, we keep it simple: just run the
            connectors and return the raw results.
        """
        # Verify investigation exists
        investigation = self.get_investigation(investigation_id)
        
        # Update status to RUNNING (Sprint 3: simple status update only)
        # Future sprints will add proper state machine transitions
        investigation.status = InvestigationStatus.RUNNING
        self._repo.update(investigation)
        
        # Execute connectors via the connector execution service
        raw_responses = await self._connector_service.execute_connectors(identifier)
        
        # Sprint 3: return raw responses as-is
        # Future sprints (M3/M4/M9) will:
        # - Persist raw responses (M9)
        # - Normalize responses (M3)
        # - Correlate entities (M4)
        # - Update investigation status to COMPLETED/FAILED
        
        return raw_responses