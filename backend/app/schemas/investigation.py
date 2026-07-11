"""
Pydantic schemas for the Investigation resource.

These define the API's request/response contracts and are intentionally
decoupled from the SQLAlchemy model (app.models.investigation) so that
storage details never leak into the API surface.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.connectors.types import ConnectorStatus, IdentifierType
from app.models.investigation import InvestigationStatus


class InvestigationCreate(BaseModel):
    """Request body for `POST /investigations`."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable case name, e.g. 'Case 2026-0417'.",
    )


class InvestigationRead(BaseModel):
    """Response body representing a single investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime


class InvestigationList(BaseModel):
    """Response body for `GET /investigations`."""

    items: list[InvestigationRead]
    count: int


class InvestigationExecuteRequest(BaseModel):
    """Request body for `POST /investigations/{id}/execute`."""

    identifier: str = Field(
        ...,
        min_length=1,
        description="The identifier value to investigate (e.g., 'example.com', 'user@example.com').",
    )
    type: IdentifierType = Field(
        ...,
        description="The type of identifier (e.g., 'domain', 'email', 'username').",
    )


class ConnectorExecutionResult(BaseModel):
    """Details of a single connector's execution result."""

    connector_name: str
    status: ConnectorStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    raw_payload_preview: str | None = Field(
        None,
        description="Brief preview of raw response for debugging. Full payload not returned in Sprint 3.",
    )


class InvestigationExecuteResponse(BaseModel):
    """Response body for `POST /investigations/{id}/execute`."""

    status: str = Field(
        ...,
        description="Overall execution status. 'running' in Sprint 3 (synchronous execution).",
    )
    connectors_executed: int = Field(
        ...,
        description="Number of connectors that were executed.",
    )
    results: list[ConnectorExecutionResult] = Field(
        ...,
        description="Per-connector execution results.",
    )