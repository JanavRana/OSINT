"""
User repository — data-access layer for the User entity.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User


class UserRepository:
    """All direct SQLAlchemy access for the User entity."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, *, email: str, full_name: str, hashed_password: str) -> User:
        """Persist a new user and return the created row."""
        user = User(email=email, full_name=full_name, hashed_password=hashed_password)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address (case-insensitive lookup)."""
        stmt = select(User).where(User.email == email.lower())
        return self._db.scalar(stmt)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key."""
        return self._db.get(User, user_id)

    def set_otp(self, user: User, code: str, expires_at: datetime) -> User:
        """Store a fresh OTP on the user row and persist."""
        user.otp_code = code
        user.otp_expires_at = expires_at
        self._db.commit()
        self._db.refresh(user)
        return user

    def verify_user(self, user: User) -> User:
        """Mark the user as verified and clear the OTP fields."""
        user.is_verified = True
        user.otp_code = None
        user.otp_expires_at = None
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, user: User) -> User:
        """Persist arbitrary changes and refresh."""
        self._db.commit()
        self._db.refresh(user)
        return user
