"""
Connector Execution Service.

Sprint 3 responsibility: orchestrate the execution of registered
connectors for a given investigation and identifier. This service sits
between the InvestigationService (which handles the high-level
investigation lifecycle) and the ConnectorManager (which runs the actual
connectors).

Per Sprint 3 requirements:
- Receives investigation + identifier
- Asks ConnectorManager to execute connectors
- Returns collected raw responses
- Stores raw responses to database
- Does NOT normalize
- Does NOT correlate
- Does NOT use Neo4j
- Runs synchronously (no background workers)

This is intentionally modular — normalization (M3) and correlation (M4)
will be added in future sprints as separate services that consume the
raw responses produced here.
"""

from __future__ import annotations

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.connectors.manager import ConnectorManager
from app.connectors.types import Identifier, RawResponseEnvelope
from app.repositories.connector_result_repository import ConnectorResultRepository


class ConnectorExecutionService:
    """
    Orchestrates connector execution for an investigation.
    
    Sprint 3 scope: run connectors, store raw responses, and return them.
    Future sprints will add normalization (M3) and correlation (M4)
    as separate services consuming this service's output.
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
        
        This method runs synchronously (from the API's perspective) per
        Sprint 3 requirements — no background workers, no job queues.
        Internally, connectors run concurrently via the ConnectorManager's
        async execution model.
        
        Args:
            investigation_id: The investigation this execution belongs to.
            identifier: The identifier to investigate (e.g., a domain,
                email, username, etc.).
            db: Database session for storing results. Uses instance session
                if not provided.
        
        Returns:
            A list of RawResponseEnvelope, one per connector executed.
            Each envelope contains either the raw response (on success)
            or error details (on failure/timeout). Per FR2.4, a single
            connector failure does not prevent other connectors from
            completing.
        
        Note:
            Raw responses are returned as-is. Normalization (M3) and
            correlation (M4) are NOT performed by this service — they
            belong to future sprints and will be separate services that
            consume these raw responses.
        """
        # The manager handles all execution logic: resolving applicable
        # connectors, running them concurrently, isolating failures, and
        # enforcing timeouts. We simply await its result.
        envelopes = await self._manager.run_all(identifier)

        # Store successful raw responses to database
        session = db or self._db
        if session is not None:
            repo = ConnectorResultRepository(session)
            for envelope in envelopes:
                if envelope.succeeded and envelope.raw_payload is not None:
                    repo.create(
                        investigation_id=investigation_id,
                        connector_name=envelope.connector_name,
                        identifier=envelope.identifier.value,
                        raw_response=envelope.raw_payload,
                    )

        return envelopes

