"""
SeedIdentifier model.

Stores the seed identifier(s) provided when an investigation is created.
Each record represents one seed input (value + type) that the investigation
was initialised with. The primary seed is used to pre-populate the
"Run all connectors" payload so investigations can be re-opened and executed
without re-entering the target.

Only one seed per investigation is used for execution (the first created),
but the model supports multiple seeds per investigation for future use.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SeedIdentifierType(str, enum.Enum):
    """Mirror of connectors/types.py IdentifierType for DB storage."""

    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    WALLET_ADDRESS = "wallet_address"
    IMAGE = "image"


class SeedIdentifier(Base):
    """A seed identifier attached to an investigation at creation time."""

    __tablename__ = "seed_identifiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SeedIdentifier id={self.id!s} "
            f"investigation_id={self.investigation_id!s} "
            f"type={self.type!r} value={self.value!r}>"
        )
