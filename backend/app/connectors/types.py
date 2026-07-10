"""
connectors/types.py

Shared data types for the Multi-Source Connector Framework (M2, Section
11.2 of MASTER_DESIGN.md).

This module defines the *shapes* connectors and their caller agree on.
It contains no HTTP logic, no real connector implementations, and no
correlation/business logic — only the vocabulary the rest of the
framework (base.py, registry.py, manager.py) is built on.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class IdentifierType(str, enum.Enum):
    """
    The six identifier types supported per Section 4.1 / FR1.1.

    This enum is the single vocabulary connectors and the registry use
    to agree on "what kind of input is this." Adding a new identifier
    type is a deliberate, rare change (unlike adding a new connector,
    which should never require touching this enum).
    """

    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    WALLET_ADDRESS = "wallet_address"
    IMAGE = "image"


@dataclass(frozen=True)
class Identifier:
    """A single investigation input: a value plus its type (FR1.1/FR1.2)."""

    value: str
    type: IdentifierType


class ConnectorStatus(str, enum.Enum):
    """
    Execution status for a single connector run against a single
    identifier (FR2.3).
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ConnectorError(Exception):
    """Base class for framework-level connector execution errors."""


class ConnectorTimeoutError(ConnectorError):
    """Raised (internally) when a connector exceeds its allotted timeout."""


class ConnectorExecutionError(ConnectorError):
    """
    Wraps any unexpected exception raised by a connector's fetch logic,
    so failures are captured as structured data (FR2.4) rather than
    propagating as unhandled exceptions.
    """

    def __init__(self, connector_name: str, original_exception: Exception):
        self.connector_name = connector_name
        self.original_exception = original_exception
        super().__init__(
            f"Connector '{connector_name}' raised "
            f"{type(original_exception).__name__}: {original_exception}"
        )


@dataclass
class RawResponseEnvelope:
    """
    The self-describing envelope every connector run produces, regardless
    of which source it came from (Section 11.2 responsibilities). This is
    what M1/M3 consume downstream — the connector framework itself does
    not interpret or normalize the `raw_payload`.

    Fields:
        connector_name: Name of the connector that produced this envelope.
        identifier: The identifier the connector was run against.
        status: Outcome of the run.
        raw_payload: The connector's untouched raw output (opaque to the
            framework). None when status is FAILED/TIMED_OUT.
        error_message: Human-readable error detail when status is
            FAILED/TIMED_OUT. None on success.
        started_at / finished_at: Execution timing, for status displays
            and provenance (FR3.3, NFR9).
        metadata: Free-form extension point for connector-specific,
            non-payload details (e.g., HTTP status code) without changing
            this envelope's shape.
    """

    connector_name: str
    identifier: Identifier
    status: ConnectorStatus
    raw_payload: Optional[Any] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == ConnectorStatus.SUCCEEDED