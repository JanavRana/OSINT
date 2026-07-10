"""
Top-level API router.

This skeleton defines ONLY the health check endpoint. Feature routers
(investigations, identifiers, orchestration status, entities, timeline,
reports, etc. — see MASTER_DESIGN.md Section 15) are out of scope here
and should be added as separate routers and included in this module
once their underlying logic exists.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)) -> dict:
    """Basic liveness/readiness check.

    Confirms the API process is up and that a database connection can be
    established. Does not check Neo4j or any connector/service logic,
    since those are out of scope for this skeleton.
    """
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    return {
        "status": "ok",
        "database": db_status,
    }
