"""
Pydantic schemas for Timeline API.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TimelineEventResponse(BaseModel):
    """Response schema for a single timeline event."""

    id: uuid.UUID = Field(description="Unique event identifier")
    investigation_id: uuid.UUID = Field(description="Parent investigation ID")
    entity_id: Optional[str] = Field(None, description="Related entity ID (if applicable)")
    occurred_at: datetime = Field(description="When the event occurred")
    event_type: str = Field(description="Type of event (e.g., 'registration', 'expiration')")
    title: str = Field(description="Human-readable event title")
    description: str = Field(description="Detailed event description")
    connector: str = Field(description="Connector that provided the source data")
    source_fact_id: uuid.UUID = Field(description="ID of the normalized fact this event came from")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from source fact")


class TimelineResponse(BaseModel):
    """Response schema for timeline list."""

    events: list[TimelineEventResponse] = Field(description="List of timeline events")
    count: int = Field(description="Total number of events returned")
