"""
Investigation API router.

Milestone 15: Complete end-to-end investigation execution pipeline.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.connectors.types import Identifier
from app.db.session import get_db
from app.schemas.investigation import (
    ConnectorExecutionResult,
    ExecutionStatistics,
    InvestigationCreate,
    InvestigationExecuteRequest,
    InvestigationExecuteResponse,
    InvestigationList,
    InvestigationRead,
)
from app.services.exceptions import NotFoundError
from app.services.investigation_service import InvestigationService

logger = logging.getLogger(__name__)

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
    summary="Execute investigation",
)
async def execute_investigation(
    investigation_id: uuid.UUID,
    payload: InvestigationExecuteRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationExecuteResponse:
    """
    Execute complete investigation pipeline.
    
    Pipeline:
    - Execute all registered connectors
    - Persist connector results
    - Run normalizers
    - Persist normalized facts
    - Return complete execution result
    """
    try:
        identifier = Identifier(value=payload.identifier, type=payload.type)
        
        logger.info(
            f"API: Executing investigation {investigation_id} for "
            f"{identifier.value} ({identifier.type})"
        )
        
        # Execute full pipeline
        execution_result = await service.execute_investigation(
            investigation_id, identifier
        )
        
        # Transform raw responses into connector results
        connector_results = [
            ConnectorExecutionResult(
                connector_name=envelope.connector_name,
                status=envelope.status,
                started_at=envelope.started_at,
                finished_at=envelope.finished_at,
                error_message=envelope.error_message,
            )
            for envelope in execution_result.raw_responses
        ]
        
        return InvestigationExecuteResponse(
            investigation_id=execution_result.investigation_id,
            status=execution_result.status,
            started_at=execution_result.started_at,
            finished_at=execution_result.finished_at,
            statistics=ExecutionStatistics(
                executed_connectors=execution_result.executed_connectors,
                successful_connectors=execution_result.successful_connectors,
                failed_connectors=execution_result.failed_connectors,
                connector_results_count=execution_result.connector_results_count,
                normalized_facts_count=execution_result.normalized_facts_count,
                execution_duration_seconds=execution_result.execution_duration_seconds,
            ),
            connector_results=connector_results,
        )
    
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(
            f"API: Investigation execution failed: {exc}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation execution failed"
        ) from exc