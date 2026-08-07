"""
Auth API router.

Endpoints:
  POST /api/v1/auth/signup      Create account + send OTP
  POST /api/v1/auth/verify-otp  Verify OTP → returns access token
  POST /api/v1/auth/login       Email + password → access token
  POST /api/v1/auth/resend-otp  Re-send OTP to unverified account
  GET  /api/v1/auth/me          Return current user (requires auth)
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    ResendOtpRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
    VerifyOtpRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new analyst account",
)
def signup(
    payload: SignupRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """
    Create an account and send a 6-digit OTP to the provided email.
    The OTP is currently printed to the server console.
    """
    user = service.register(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    return UserRead(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify email OTP and receive access token",
)
def verify_otp(
    payload: VerifyOtpRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Validate the OTP. On success the account is marked verified and a JWT is returned."""
    user, token = service.verify_otp(email=payload.email, otp=payload.otp)
    return TokenResponse(
        access_token=token,
        user=UserRead(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email + password",
)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Return a JWT access token on successful credential validation."""
    user, token = service.login(email=payload.email, password=payload.password)
    return TokenResponse(
        access_token=token,
        user=UserRead(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/resend-otp",
    status_code=status.HTTP_200_OK,
    summary="Resend OTP to unverified account",
)
def resend_otp(
    payload: ResendOtpRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    service.resend_otp(email=payload.email)
    return {"message": "OTP resent. Check server logs."}


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return current authenticated user",
)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )
