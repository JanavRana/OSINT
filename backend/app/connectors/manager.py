"""
connectors/manager.py

Execution plumbing for the Multi-Source Connector Framework (M2,
Section 11.2 of MASTER_DESIGN.md).

ConnectorManager answers: "given this identifier, which registered
connectors apply, and what did each of them return?" It has no concept
of an "investigation," performs no persistence, and does not decide
*when* to run (that is M1's — the Search Orchestrator's — job, which
depends on this manager rather than reimplementing it). This module
also performs no HTTP requests and no normalization/correlation logic;
it only dispatches to whatever connectors are registered and collects
their envelopes.

Concurrency: connectors are run concurrently for a given identifier
(Section 17: async execution model), and a failure in one connector
never prevents the others from completing (FR2.4, NFR5) — each
connector's `run()` (see base.py) already isolates its own errors, so
the manager simply gathers results without a top-level try/except per
connector.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Type

from .base import BaseConnector
from .registry import ConnectorRegistry, registry as default_registry
from .types import Identifier, RawResponseEnvelope


class ConnectorManager:
    """
    Resolves and executes the connectors applicable to a given
    identifier, using a ConnectorRegistry to determine which connectors
    apply (FR2.1/FR2.2).

    This class intentionally does not know about investigations,
    status persistence, or normalization — see M1 (Search Orchestrator)
    and M3 (Normalization Engine) in MASTER_DESIGN.md for those
    responsibilities, which are built on top of this manager rather
    than duplicated here.
    """

    def __init__(self, connector_registry: Optional[ConnectorRegistry] = None):
        self._registry = connector_registry or default_registry

    def resolve_connectors(self, identifier: Identifier) -> List[Type[BaseConnector]]:
        """
        Return the connector classes registered as applicable to this
        identifier's type (FR2.1). Manual opt-out/override, if ever
        needed, is a concern for the caller (e.g. M1), not this method.
        """
        return self._registry.get_connectors_for_identifier_type(identifier.type)

    async def run_all(
        self,
        identifier: Identifier,
        connector_classes: Optional[List[Type[BaseConnector]]] = None,
    ) -> List[RawResponseEnvelope]:
        """
        Instantiate and run every applicable connector for `identifier`
        concurrently, returning one RawResponseEnvelope per connector
        (FR2.2, FR2.4).

        Args:
            identifier: The identifier to run connectors against.
            connector_classes: Optional explicit list of connector
                classes to run instead of resolving them from the
                registry (e.g. for a caller that wants to opt out of
                some connectors). Defaults to `resolve_connectors`.

        Each connector's own `run()` method (base.py) already isolates
        that connector's failures/timeouts into its envelope, so no
        additional exception handling is needed here — a bug in one
        connector's `fetch()` cannot prevent the others' envelopes from
        being returned.
        """
        classes = (
            connector_classes
            if connector_classes is not None
            else self.resolve_connectors(identifier)
        )

        if not classes:
            return []

        instances = [connector_cls() for connector_cls in classes]
        return await asyncio.gather(*(instance.run(identifier) for instance in instances))