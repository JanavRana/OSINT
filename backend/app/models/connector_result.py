"""
ConnectorResult model.

Stores raw responses from connector executions. Each record represents
a single connector's output for a specific identifier within an
investigation.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ConnectorResult(Base):
    """Raw connector execution result storage."""

    __tablename__ = "connector_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector_name: Mapped[str] = mapped_column(String(255), nullable=False)
    identifier: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (
            f"<ConnectorResult id={self.id!s} "
            f"investigation_id={self.investigation_id!s} "
            f"connector_name={self.connector_name!r}>"
        )
