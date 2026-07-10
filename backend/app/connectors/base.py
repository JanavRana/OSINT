"""
connectors/base.py

The connector interface for the Multi-Source Connector Framework (M2,
Section 11.2 of MASTER_DESIGN.md).

This module defines the single contract every OSINT source connector
(WHOIS, RDAP, crt.sh, Wayback Machine, GitHub, Gravatar, and any future
source) must implement. It contains NO real connector logic, NO HTTP
calls, and NO business/correlation logic — only the abstract shape and
the generic execution wrapper that turns a connector's raw output into
a self-describing envelope (FR3.2's precondition) while isolating
failures (FR2.4) and enforcing a timeout (NFR6).

Concrete connectors (implemented elsewhere, e.g. connectors/whois/) are
expected to:
    1. Subclass BaseConnector.
    2. Set `name` and `supported_identifier_types`.
    3. Implement `fetch()` with real source-specific logic.
    4. Register themselves via the registry (see registry.py) — this
       file does not know about, or import, any concrete connector.
"""

from __future__ import annotations

import abc
import asyncio
from datetime import datetime, timezone
from typing import Any, ClassVar, FrozenSet

from .types import (
    ConnectorExecutionError,
    ConnectorStatus,
    ConnectorTimeoutError,
    Identifier,
    IdentifierType,
    RawResponseEnvelope,
)

# Default per-connector timeout (seconds). A single slow/unresponsive
# source must not stall the rest of an investigation (NFR5, NFR6).
# Concrete connectors may override this via `timeout_seconds`.
DEFAULT_TIMEOUT_SECONDS: float = 15.0


class BaseConnector(abc.ABC):
    """
    Abstract base class every OSINT source connector implements.

    This class defines *what* a connector is (name, the identifier
    types it handles, a `fetch` method) and provides the *shared
    execution plumbing* (timing, timeout enforcement, error isolation,
    envelope construction) so that concrete connectors only need to
    implement `fetch()` — the one piece of source-specific logic.
    """

    #: Unique, stable name for this connector (e.g. "whois"). Concrete
    #: subclasses must override this.
    name: ClassVar[str] = ""

    #: The identifier types this connector can be applied to. Concrete
    #: subclasses must override this. Used by the registry (registry.py)
    #: to build the identifier-type -> connectors mapping (FR2.1).
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset()

    #: Per-connector timeout override. Falls back to
    #: DEFAULT_TIMEOUT_SECONDS if not set by a subclass.
    timeout_seconds: ClassVar[float] = DEFAULT_TIMEOUT_SECONDS

    @abc.abstractmethod
    async def fetch(self, identifier: Identifier) -> Any:
        """
        Perform the actual lookup against this connector's OSINT source
        and return the raw, untouched result.

        This method contains no shared plumbing of its own — it is pure
        source-specific logic, implemented by concrete connectors (not
        part of this framework task). It must NOT be implemented here.

        Raises:
            Any exception on failure; `run()` below is responsible for
            catching and wrapping it. Implementations should not need
            to handle timeouts themselves — `run()` enforces those.
        """
        raise NotImplementedError

    async def run(self, identifier: Identifier) -> RawResponseEnvelope:
        """
        Execute this connector against a single identifier and return a
        self-describing RawResponseEnvelope, regardless of success or
        failure (Section 11.2: "Ensure each connector's raw response is
        returned in a self-describing envelope").

        Responsibilities handled here (framework plumbing only):
            - Confirm the identifier type is supported.
            - Track start/finish timestamps.
            - Enforce `timeout_seconds`.
            - Catch any exception raised by `fetch()` and convert it
              into a FAILED/TIMED_OUT envelope instead of propagating
              it (FR2.4, NFR5) — so one connector's failure can never
              take down orchestration of the others.

        This method performs no HTTP requests itself and contains no
        normalization, correlation, or other business logic.
        """
        if identifier.type not in self.supported_identifier_types:
            raise ValueError(
                f"Connector '{self.name}' does not support identifier "
                f"type '{identifier.type}'."
            )

        started_at = datetime.now(timezone.utc)

        try:
            raw_payload = await asyncio.wait_for(
                self.fetch(identifier), timeout=self.timeout_seconds
            )
            finished_at = datetime.now(timezone.utc)
            return RawResponseEnvelope(
                connector_name=self.name,
                identifier=identifier,
                status=ConnectorStatus.SUCCEEDED,
                raw_payload=raw_payload,
                started_at=started_at,
                finished_at=finished_at,
            )
        except asyncio.TimeoutError:
            finished_at = datetime.now(timezone.utc)
            timeout_error = ConnectorTimeoutError(
                f"Connector '{self.name}' timed out after "
                f"{self.timeout_seconds}s."
            )
            return RawResponseEnvelope(
                connector_name=self.name,
                identifier=identifier,
                status=ConnectorStatus.TIMED_OUT,
                error_message=str(timeout_error),
                started_at=started_at,
                finished_at=finished_at,
            )
        except Exception as exc:  # noqa: BLE001 - intentional catch-all
            finished_at = datetime.now(timezone.utc)
            wrapped = ConnectorExecutionError(self.name, exc)
            return RawResponseEnvelope(
                connector_name=self.name,
                identifier=identifier,
                status=ConnectorStatus.FAILED,
                error_message=str(wrapped),
                started_at=started_at,
                finished_at=finished_at,
            )