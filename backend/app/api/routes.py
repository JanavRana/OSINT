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
from app.api.v1.auth import router as auth_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.graph import router as graph_router
from app.api.v1.risk import router as risk_router
from app.api.v1.search import router as search_router
from app.api.v1.statistics import router as statistics_router

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

v1_router = APIRouter()

v1_router.include_router(
    auth_router,
    tags=["Auth"],
)

v1_router.include_router(
    investigations_router,
    prefix="/investigations",
    tags=["Investigations"],
)

v1_router.include_router(
    graph_router,
    tags=["Graph"],
)

v1_router.include_router(
    risk_router,
    tags=["Risk"],
)

v1_router.include_router(
    search_router,
    tags=["Search"],
)

v1_router.include_router(
    statistics_router,
    tags=["Statistics"],
)

router.include_router(v1_router)