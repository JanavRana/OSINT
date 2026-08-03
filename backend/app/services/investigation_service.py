"""
Investigation service.

Milestone 15: Complete end-to-end investigation execution pipeline.
Orchestrates connector execution, result persistence, normalization,
and fact persistence.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.connectors.types import Identifier, RawResponseEnvelope
from app.models.investigation import Investigation, InvestigationStatus
from app.models.normalized_fact import NormalizedFact
from app.models.seed_identifier import SeedIdentifier
from app.normalizers.manager import normalization_manager
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.normalized_fact_repository import NormalizedFactRepository
from app.repositories.seed_identifier_repository import SeedIdentifierRepository
from app.services.connector_execution_service import ConnectorExecutionService
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class InvestigationExecutionResult:
    """Complete execution result for an investigation."""
    
    investigation_id: uuid.UUID
    status: InvestigationStatus
    executed_connectors: int
    successful_connectors: int
    failed_connectors: int
    connector_results_count: int
    normalized_facts_count: int
    execution_duration_seconds: float
    started_at: datetime
    finished_at: datetime
    raw_responses: List[RawResponseEnvelope]


class InvestigationService:
    """Business logic for creating and retrieving investigations."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = InvestigationRepository(db)
        self._fact_repo = NormalizedFactRepository(db)
        self._connector_service = ConnectorExecutionService()
    
    async def get_correlated_entities(self, investigation_id: uuid.UUID):
        """
        Get correlated entities for an investigation.
        
        Placeholder - requires correlation results to be persisted.
        """
        from ..correlation.types import CorrelatedEntities
        return CorrelatedEntities()
        self._connector_service = ConnectorExecutionService(db=db)
        self._fact_repo = NormalizedFactRepository(db)
        self._seed_repo = SeedIdentifierRepository(db)

    def create_investigation(
        self,
        *,
        name: str,
        seed_value: str | None = None,
        seed_type: str | None = None,
    ) -> tuple[Investigation, SeedIdentifier | None]:
        """
        Create a new investigation, optionally with a primary seed identifier.

        Returns:
            A tuple of (Investigation, SeedIdentifier | None).
        """
        investigation = self._repo.create(name=name)
        seed: SeedIdentifier | None = None
        if seed_value and seed_type:
            seed = self._seed_repo.create(
                investigation_id=investigation.id,
                value=seed_value,
                identifier_type=seed_type,
            )
        return investigation, seed


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
    ) -> InvestigationExecutionResult:
        """
        Execute complete investigation pipeline.
        
        Pipeline:
        1. Verify investigation exists
        2. Update status to RUNNING
        3. Execute all registered connectors
        4. Persist connector results
        5. Run normalizers on successful results
        6. Persist normalized facts
        7. Update investigation status (COMPLETED/FAILED)
        8. Return execution result
        
        Args:
            investigation_id: The investigation to execute.
            identifier: The identifier to investigate.
        
        Returns:
            InvestigationExecutionResult with complete execution details.
        
        Raises:
            NotFoundError: If the investigation does not exist.
        """
        started_at = datetime.now(timezone.utc)
        
        logger.info(
            f"Starting investigation execution: investigation_id={investigation_id}, "
            f"identifier={identifier.value} ({identifier.type})"
        )
        
        # Verify investigation exists
        investigation = self.get_investigation(investigation_id)
        
        # Update status to RUNNING
        investigation.status = InvestigationStatus.RUNNING
        self._repo.update(investigation)
        logger.info(f"Investigation {investigation_id} status updated to RUNNING")
        
        try:
            # Execute connectors and persist results
            raw_responses = await self._connector_service.execute_connectors(
                investigation_id=investigation_id,
                identifier=identifier,
                db=self._db
            )
            
            executed_count = len(raw_responses)
            successful_count = sum(1 for r in raw_responses if r.succeeded)
            failed_count = executed_count - successful_count
            
            logger.info(
                f"Connector execution complete: {executed_count} executed, "
                f"{successful_count} succeeded, {failed_count} failed"
            )
            
            # Run normalizers on successful results
            normalization_results = normalization_manager.normalize_batch(raw_responses)
            
            logger.info(f"Normalization complete: {len(normalization_results)} results")
            
            # Persist normalized facts
            facts_persisted = 0
            for norm_result in normalization_results:
                for fact in norm_result.facts:
                    try:
                        self._fact_repo.create(
                            investigation_id=investigation_id,
                            connector_name=fact.source_connector,
                            fact_type=fact.fact_type.value,
                            value=str(fact.value),
                            confidence=fact.confidence,
                            fact_metadata=fact.metadata,
                            occurred_at=fact.occurred_at or datetime.now(timezone.utc),
                        )
                        facts_persisted += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to persist fact from {fact.source_connector}: {e}",
                            exc_info=True
                        )
                        # Continue processing other facts
            
            logger.info(f"Persisted {facts_persisted} normalized facts")
            
            # Update investigation status to COMPLETED
            investigation.status = InvestigationStatus.COMPLETED
            self._repo.update(investigation)
            
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            logger.info(
                f"Investigation {investigation_id} completed successfully in {duration:.2f}s"
            )
            
            return InvestigationExecutionResult(
                investigation_id=investigation_id,
                status=InvestigationStatus.COMPLETED,
                executed_connectors=executed_count,
                successful_connectors=successful_count,
                failed_connectors=failed_count,
                connector_results_count=successful_count,
                normalized_facts_count=facts_persisted,
                execution_duration_seconds=duration,
                started_at=started_at,
                finished_at=finished_at,
                raw_responses=raw_responses,
            )
            
        except Exception as e:
            logger.error(
                f"Investigation {investigation_id} failed: {type(e).__name__}: {e}",
                exc_info=True
            )
            
            # Update investigation status to FAILED
            investigation.status = InvestigationStatus.FAILED
            self._repo.update(investigation)
            
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            return InvestigationExecutionResult(
                investigation_id=investigation_id,
                status=InvestigationStatus.FAILED,
                executed_connectors=0,
                successful_connectors=0,
                failed_connectors=0,
                connector_results_count=0,
                normalized_facts_count=0,
                execution_duration_seconds=duration,
                started_at=started_at,
                finished_at=finished_at,
                raw_responses=[],
            )