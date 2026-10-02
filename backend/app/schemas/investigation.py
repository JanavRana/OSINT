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


class SeedIdentifierSchema(BaseModel):
    """Embedded seed identifier within investigation create/read."""

    value: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The seed identifier value, e.g. 'example.com'.",
    )
    type: IdentifierType = Field(
        ...,
        description="The identifier type, e.g. 'domain', 'email'.",
    )


class InvestigationCreate(BaseModel):
    """Request body for `POST /investigations`."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable case name, e.g. 'Case 2026-0417'.",
    )
    seed_identifier: SeedIdentifierSchema | None = Field(
        None,
        description="Optional primary seed identifier to persist with the investigation.",
    )


class InvestigationRead(BaseModel):
    """Response body representing a single investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime
    seed_identifier: SeedIdentifierSchema | None = None


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


# --- Identifiers & connector results (read-only) ----------------------------


class IdentifierRead(BaseModel):
    """A single identifier extracted from normalized facts."""

    id: str
    type: str
    value: str
    confidence: float
    sources: int
    first_seen: str
    profile_url: str | None = None
    platform: str | None = Field(
        None,
        description="Platform name for username identifiers (e.g., 'github', 'reddit').",
    )
    platform_display_name: str | None = Field(
        None,
        description="Human-readable platform name (e.g., 'GitHub', 'Reddit').",
    )


class IdentifierListResponse(BaseModel):
    """Response body for `GET /investigations/{id}/identifiers`."""

    items: list[IdentifierRead]
    count: int


class ConnectorResultRead(BaseModel):
    """Summary of a single connector's execution for listing."""

    id: str
    name: str
    category: str
    status: str
    hits: int
    runtime: str
    error_message: str | None = None


class ConnectorResultListResponse(BaseModel):
    """Response body for `GET /investigations/{id}/connectors`."""

    items: list[ConnectorResultRead]
    count: int