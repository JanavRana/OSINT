"""
Investigation API router.

Implements the three Sprint 2 endpoints from MASTER_DESIGN.md Section 15:

    POST /investigations        - create a new investigation
    GET  /investigations        - list investigations (paginated)
    GET  /investigations/{id}   - retrieve a single investigation

The router is a thin HTTP layer: it validates/parses input via Pydantic
schemas, delegates to InvestigationService, and translates service-layer
outcomes into HTTP responses/status codes. No business logic or direct
database access lives here.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationList,
    InvestigationRead,
)
from app.services.exceptions import NotFoundError
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigations", tags=["investigations"])


def get_investigation_service(db: Session = Depends(get_db)) -> InvestigationService:
    """FastAPI dependency that builds an InvestigationService per request."""
    return InvestigationService(db)


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new investigation",
)
def create_investigation(
    payload: InvestigationCreate,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRead:
    investigation = service.create_investigation(name=payload.name)
    return InvestigationRead.model_validate(investigation)


@router.get(
    "",
    response_model=InvestigationList,
    summary="List investigations",
)
def list_investigations(
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of records to return."
    ),
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationList:
    items, total = service.list_investigations(skip=skip, limit=limit)
    return InvestigationList(
        items=[InvestigationRead.model_validate(item) for item in items],
        count=total,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationRead,
    summary="Retrieve a single investigation",
)
def get_investigation(
    investigation_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRead:
    try:
        investigation = service.get_investigation(investigation_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return InvestigationRead.model_validate(investigation)