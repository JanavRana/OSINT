"""
Top-level API router.

Registers:
- Health endpoint
- Versioned API routers

Feature-specific endpoints live under app/api/v1/.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.investigations import router as investigations_router

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)) -> dict:
    """Basic liveness/readiness check."""

    db_status = "ok"

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    return {
        "status": "ok",
        "database": db_status,
    }


# -------------------------
# API Version 1
# -------------------------

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(
    investigations_router,
    prefix="/investigations",
    tags=["Investigations"],
)

router.include_router(v1_router)