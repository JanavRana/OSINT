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

from app.connectors.types import Identifier, IdentifierType, RawResponseEnvelope
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
        self._seed_repo = SeedIdentifierRepository(db)
    
    async def get_correlated_entities(self, investigation_id: uuid.UUID):
        """
        Get correlated entities for an investigation.
        
        Placeholder - requires correlation results to be persisted.
        """
        from ..correlation.types import CorrelatedEntities
        return CorrelatedEntities()

    def create_investigation(
        self,
        *,
        name: str,
        seed_value: str | None = None,
        seed_type: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[Investigation, SeedIdentifier | None]:
        """
        Create a new investigation, optionally with a primary seed identifier.

        Returns:
            A tuple of (Investigation, SeedIdentifier | None).
        """
        investigation = self._repo.create(name=name, user_id=user_id)
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
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[Investigation], int]:
        """Return a page of investigations (filtered by user) and the total count."""
        return self._repo.list(skip=skip, limit=limit, user_id=user_id)

    def delete_investigation(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Delete an investigation by ID after verifying ownership.

        Raises:
            NotFoundError: Investigation does not exist.
            HTTPException 403: Caller does not own the investigation.
        """
        from fastapi import HTTPException, status

        investigation = self._repo.get_by_id(investigation_id)
        if investigation is None:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        if investigation.user_id is not None and investigation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this investigation.",
            )
        self._repo.delete(investigation)

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
            # --- Route by identifier type ---
            if identifier.type == IdentifierType.USERNAME:
                # Username investigations use the identity framework dispatcher
                raw_responses = await self._run_username_osint(
                    investigation_id=investigation_id,
                    username=identifier.value,
                )
            else:
                # Domain/email/phone/IP use the classic connector framework
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
            
            # Persist normalized facts (with deduplication)
            facts_persisted = 0
            skipped_duplicates = 0
            for norm_result in normalization_results:
                for fact in norm_result.facts:
                    try:
                        created = self._fact_repo.create_if_not_exists(
                            investigation_id=investigation_id,
                            connector_name=fact.source_connector,
                            fact_type=fact.fact_type.value,
                            value=str(fact.value),
                            confidence=fact.confidence,
                            fact_metadata=fact.metadata,
                            occurred_at=fact.occurred_at or datetime.now(timezone.utc),
                        )
                        if created is not None:
                            facts_persisted += 1
                        else:
                            skipped_duplicates += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to persist fact from {fact.source_connector}: {e}",
                            exc_info=True
                        )
                        # Continue processing other facts
            
            if skipped_duplicates:
                logger.info(f"Skipped {skipped_duplicates} duplicate facts")
            logger.info(f"Persisted {facts_persisted} normalized facts")

            # --- Create graph relationships for username facts (non-blocking) ---
            if identifier.type == IdentifierType.USERNAME and facts_persisted > 0:
                await self._create_username_graph_relationships(
                    investigation_id=investigation_id,
                    username=identifier.value,
                    normalization_results=normalization_results,
                )
            
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

    async def _run_username_osint(
        self,
        investigation_id: uuid.UUID,
        username: str,
    ) -> List[RawResponseEnvelope]:
        """
        Run username OSINT via the identity framework dispatcher.

        Routes username investigations to the 38 YAML platform definitions
        instead of the classic connector framework (which has no USERNAME
        connectors registered).

        Args:
            investigation_id: Investigation ID
            username: Username to investigate

        Returns:
            List of RawResponseEnvelope from all platform checks
        """
        try:
            from app.identity.username.dispatcher import dispatch_username_osint
            envelopes = await dispatch_username_osint(
                username=username,
                investigation_id=investigation_id,
            )
            logger.info(
                f"Username OSINT returned {len(envelopes)} envelopes "
                f"for {username!r}"
            )
            return envelopes
        except Exception as e:
            logger.error(
                f"Username OSINT dispatcher failed for {username!r}: {e}",
                exc_info=True,
            )
            return []

    async def _create_username_graph_relationships(
        self,
        investigation_id: uuid.UUID,
        username: str,
        normalization_results: list,
    ) -> None:
        """
        Create graph relationships for discovered username platform accounts.

        Creates FOUND_ON relationship facts stored in normalized_facts so they
        appear in GET /identifiers and the graph endpoint without requiring Neo4j.

        Falls back gracefully on any error — this is non-blocking.
        """
        try:
            from app.normalizers.types import FactType
            found_platforms = []
            for norm_result in normalization_results:
                for fact in norm_result.facts:
                    if fact.fact_type == FactType.PROFILE_DATA:
                        meta = fact.metadata or {}
                        if meta.get("exists") is True:
                            found_platforms.append({
                                "platform_id": meta.get("platform_id", ""),
                                "platform_display_name": meta.get("platform_display_name", ""),
                                "profile_url": meta.get("profile_url", ""),
                                "confidence": fact.confidence,
                            })

            if not found_platforms:
                return

            logger.info(
                f"Creating graph relationship facts for {username!r}: "
                f"{len(found_platforms)} platforms found"
            )

            for platform_info in found_platforms:
                try:
                    self._fact_repo.create_if_not_exists(
                        investigation_id=investigation_id,
                        connector_name="username_graph",
                        fact_type="social_account",
                        value=f"{username}@{platform_info['platform_id']}",
                        confidence=platform_info["confidence"],
                        fact_metadata={
                            "username": username,
                            "platform": platform_info["platform_id"],
                            "platform_display_name": platform_info["platform_display_name"],
                            "profile_url": platform_info["profile_url"],
                            "relationship": "FOUND_ON",
                            "graph_edge": True,
                        },
                        occurred_at=datetime.now(timezone.utc),
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not create graph fact for "
                        f"{username}@{platform_info['platform_id']}: {e}"
                    )

        except Exception as e:
            logger.warning(
                f"Graph relationship creation failed (non-blocking): {e}",
                exc_info=True,
            )