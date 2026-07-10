"""
Pydantic schemas for the Investigation resource.

These define the API's request/response contracts and are intentionally
decoupled from the SQLAlchemy model (app.models.investigation) so that
storage details never leak into the API surface.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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