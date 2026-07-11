"""
Investigation API router.

Implements the Sprint 2 endpoints from MASTER_DESIGN.md Section 15:

    POST /investigations        - create a new investigation
    GET  /investigations        - list investigations (paginated)
    GET  /investigations/{id}   - retrieve a single investigation

Sprint 3 extension: adds connector execution endpoint:

    POST /investigations/{id}/execute - execute connectors for an identifier
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.connectors.types import Identifier
from app.db.session import get_db
from app.schemas.investigation import (
    ConnectorExecutionResult,
    InvestigationCreate,
    InvestigationExecuteRequest,
    InvestigationExecuteResponse,
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


@router.post(
    "/{investigation_id}/execute",
    response_model=InvestigationExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute connectors for an investigation",
)
async def execute_investigation(
    investigation_id: uuid.UUID,
    payload: InvestigationExecuteRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationExecuteResponse:
    """
    Execute registered connectors for a given identifier within an investigation.
    
    Sprint 3 scope:
    - Runs connectors synchronously (no background workers)
    - Returns raw connector execution results
    - Does NOT persist results (future sprint)
    - Does NOT normalize or correlate (future sprints M3/M4)
    
    The investigation's status is updated to 'running' before execution.
    Future sprints will add proper status transitions and result persistence.
    """
    try:
        # Convert request payload to Identifier
        identifier = Identifier(value=payload.identifier, type=payload.type)
        
        # Execute connectors via the service
        raw_responses = await service.execute_investigation(investigation_id, identifier)
        
        # Transform raw responses into API response format
        results = []
        for envelope in raw_responses:
            # Provide a brief preview of raw payload for debugging
            # (full payload not returned in Sprint 3)
            preview = None
            if envelope.raw_payload is not None:
                payload_str = str(envelope.raw_payload)
                preview = (
                    payload_str[:100] + "..."
                    if len(payload_str) > 100
                    else payload_str
                )
            
            results.append(
                ConnectorExecutionResult(
                    connector_name=envelope.connector_name,
                    status=envelope.status,
                    started_at=envelope.started_at,
                    finished_at=envelope.finished_at,
                    error_message=envelope.error_message,
                    raw_payload_preview=preview,
                )
            )
        
        return InvestigationExecuteResponse(
            status="running",
            connectors_executed=len(results),
            results=results,
        )
    
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc