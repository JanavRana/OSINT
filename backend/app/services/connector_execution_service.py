"""
Connector Execution Service.

Milestone 15: Orchestrates connector execution and persists results.
Executes all registered connectors independently, handling failures
gracefully.
"""

from __future__ import annotations

import logging
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.connectors.manager import ConnectorManager
from app.connectors.types import Identifier, RawResponseEnvelope
from app.repositories.connector_result_repository import ConnectorResultRepository

logger = logging.getLogger(__name__)


class ConnectorExecutionService:
    """
    Orchestrates connector execution for an investigation.
    
    Milestone 15: Executes connectors independently, persists successful
    results, and returns all envelopes (success and failure).
    """

    def __init__(
        self,
        connector_manager: ConnectorManager | None = None,
        db: Session | None = None,
    ) -> None:
        """
        Initialize the service with an optional ConnectorManager and database session.
        
        Args:
            connector_manager: The manager that resolves and runs
                connectors. Defaults to a new instance if not provided.
            db: Database session for storing results. Optional, can be
                provided later via execute_connectors.
        """
        self._manager = connector_manager or ConnectorManager()
        self._db = db

    async def execute_connectors(
        self,
        investigation_id: uuid.UUID,
        identifier: Identifier,
        db: Session | None = None,
    ) -> List[RawResponseEnvelope]:
        """
        Execute all registered connectors applicable to the given identifier.
        
        Connectors are executed independently. Failures do not stop the
        pipeline. All successful raw responses are persisted.
        
        Args:
            investigation_id: The investigation this execution belongs to.
            identifier: The identifier to investigate.
            db: Database session for storing results. Uses instance session
                if not provided.
        
        Returns:
            A list of RawResponseEnvelope, one per connector executed.
            Each envelope contains either the raw response (on success)
            or error details (on failure/timeout).
        """
        logger.info(
            f"Executing connectors for investigation {investigation_id}, "
            f"identifier={identifier.value} ({identifier.type})"
        )
        
        # Execute all connectors via the manager
        envelopes = await self._manager.run_all(identifier)
        
        # Store successful raw responses to database
        session = db or self._db
        if session is not None:
            repo = ConnectorResultRepository(session)
            stored_count = 0
            
            for envelope in envelopes:
                if envelope.succeeded and envelope.raw_payload is not None:
                    try:
                        repo.create(
                            investigation_id=investigation_id,
                            connector_name=envelope.connector_name,
                            identifier=envelope.identifier.value,
                            raw_response=envelope.raw_payload,
                        )
                        stored_count += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to persist connector result for {envelope.connector_name}: {e}",
                            exc_info=True
                        )
                        # Continue processing other results
            
            logger.info(f"Persisted {stored_count} connector results")

        return envelopes

