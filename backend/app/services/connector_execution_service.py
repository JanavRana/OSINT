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
- Does NOT normalize
- Does NOT correlate
- Does NOT use Neo4j
- Runs synchronously (no background workers)

This is intentionally modular — normalization (M3) and correlation (M4)
will be added in future sprints as separate services that consume the
raw responses produced here.
"""

from __future__ import annotations

from typing import List

from app.connectors.manager import ConnectorManager
from app.connectors.types import Identifier, RawResponseEnvelope


class ConnectorExecutionService:
    """
    Orchestrates connector execution for an investigation.
    
    Sprint 3 scope: run connectors and return raw responses only.
    Future sprints will add normalization (M3) and correlation (M4)
    as separate services consuming this service's output.
    """

    def __init__(self, connector_manager: ConnectorManager | None = None) -> None:
        """
        Initialize the service with an optional ConnectorManager.
        
        Args:
            connector_manager: The manager that resolves and runs
                connectors. Defaults to a new instance if not provided.
        """
        self._manager = connector_manager or ConnectorManager()

    async def execute_connectors(
        self, identifier: Identifier
    ) -> List[RawResponseEnvelope]:
        """
        Execute all registered connectors applicable to the given identifier.
        
        This method runs synchronously (from the API's perspective) per
        Sprint 3 requirements — no background workers, no job queues.
        Internally, connectors run concurrently via the ConnectorManager's
        async execution model.
        
        Args:
            identifier: The identifier to investigate (e.g., a domain,
                email, username, etc.).
        
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
        return await self._manager.run_all(identifier)
