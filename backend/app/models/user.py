"""
User model for authentication.

Stores analyst accounts. Users must verify their email via OTP before they
can log in. All investigations are scoped to a user via user_id FK.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    """Analyst/operator account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # OTP fields — set on signup / resend, cleared after verification
    otp_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    # Relationship to investigations (back-populates from Investigation.user)
    investigations: Mapped[list] = relationship(
        "Investigation", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id!s} email={self.email!r} verified={self.is_verified}>"
