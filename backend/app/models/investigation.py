"""
Investigation model.

Per MASTER_DESIGN.md Section 11.9 (M9 — Investigation & Persistence
Layer), the `Investigation` is the top-level parent record that every
other module's data (identifiers, raw responses, normalized facts,
unified entities, reports) will eventually hang off of.

Sprint 2 implements ONLY the Investigation entity itself. Relationships
to identifiers, connector executions, facts, entities, and reports are
intentionally not modeled yet — those belong to later sprints/modules
and will be added as foreign keys / relationships without needing to
change this model's shape.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InvestigationStatus(str, enum.Enum):
    """Lifecycle status of an investigation.

    Kept intentionally minimal for Sprint 2. Later sprints (orchestration,
    correlation) may transition an investigation through these states, but
    no such transition logic is implemented here.
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Investigation(Base):
    """The top-level case record (MASTER_DESIGN.md Section 11.9)."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(
            InvestigationStatus,
            name="investigation_status",
            # Store the lowercase `.value` (e.g. "created") as the
            # Postgres enum label instead of SQLAlchemy's default of the
            # Python member name (e.g. "CREATED"), so it matches
            # server_default below and any raw SQL/tooling that expects
            # the lowercase form used elsewhere (API responses, etc).
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=InvestigationStatus.CREATED,
        server_default=InvestigationStatus.CREATED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Investigation id={self.id!s} name={self.name!r} status={self.status!s}>"