"""
Auth service — business logic for user registration, OTP verification, and login.
"""

import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_otp,
    get_otp_expiry,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
settings = get_settings()


def _send_otp_email(email: str, otp: str) -> None:
    """
    Send the OTP to the user via EmailService.
    """
    try:
        EmailService.send_otp_email(email, otp)
        logger.info(f"Successfully sent OTP to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again later."
        )


class AuthService:
    def __init__(self, db: Session) -> None:
        self._repo = UserRepository(db)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, email: str, full_name: str, password: str) -> User:
        """
        Create a new unverified user and send an OTP.

        Raises HTTP 409 if the email is already registered.
        """
        email = email.lower().strip()
        existing = self._repo.get_by_email(email)
        if existing:
            # If already registered but not verified, re-send OTP
            if not existing.is_verified:
                return self._resend_otp(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        hashed = hash_password(password)
        user = self._repo.create(email=email, full_name=full_name, hashed_password=hashed)
        otp = generate_otp()
        user = self._repo.set_otp(user, otp, get_otp_expiry())
        _send_otp_email(email, otp)
        return user

    def _resend_otp(self, user: User) -> User:
        """Generate a fresh OTP for an unverified user."""
        otp = generate_otp()
        user = self._repo.set_otp(user, otp, get_otp_expiry())
        _send_otp_email(user.email, otp)
        return user

    def resend_otp(self, email: str) -> None:
        """Public resend — raises 404 if no account exists."""
        email = email.lower().strip()
        user = self._repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found for this email.",
            )
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already verified.",
            )
        self._resend_otp(user)

    # ── OTP Verification ─────────────────────────────────────────────────────

    def verify_otp(self, email: str, otp: str) -> tuple[User, str]:
        """
        Validate the OTP and mark the user as verified.

        Returns (user, access_token) so the client can log in immediately.
        Raises HTTP 400/404 for invalid OTP or expired code.
        """
        from datetime import datetime, timezone

        email = email.lower().strip()
        user = self._repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found for this email.",
            )
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already verified. Please log in.",
            )
        if not user.otp_code or user.otp_code != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code.",
            )
        if not user.otp_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        # Compare timezone-aware datetimes
        expires_at = user.otp_expires_at
        if expires_at.tzinfo is None:
            from datetime import timezone
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        user = self._repo.verify_user(user)
        token = self._make_token(user)
        return user, token

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> tuple[User, str]:
        """
        Validate credentials and return (user, access_token).

        Raises HTTP 401 for wrong credentials and HTTP 403 if unverified.
        """
        email = email.lower().strip()
        user = self._repo.get_by_email(email)
        
        if not user:
            logger.warning(f"Login failed: No user found for email '{email}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )
            
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Login failed: Password mismatch for email '{email}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your OTP.",
            )
        token = self._make_token(user)
        return user, token

    # ── Internal ──────────────────────────────────────────────────────────────

    def _make_token(self, user: User) -> str:
        return create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
