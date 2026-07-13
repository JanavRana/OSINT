"""
Pydantic schemas for the Investigation resource.

Milestone 15: Extended with complete execution result schemas.
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


class ExecutionStatistics(BaseModel):
    """Execution statistics."""

    executed_connectors: int
    successful_connectors: int
    failed_connectors: int
    connector_results_count: int
    normalized_facts_count: int
    execution_duration_seconds: float


class InvestigationExecuteResponse(BaseModel):
    """Response body for `POST /investigations/{id}/execute`."""

    investigation_id: uuid.UUID
    status: InvestigationStatus = Field(
        ...,
        description="Final investigation status after execution.",
    )
    started_at: datetime
    finished_at: datetime
    statistics: ExecutionStatistics
    connector_results: list[ConnectorExecutionResult]