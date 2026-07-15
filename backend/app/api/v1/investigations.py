"""
Investigation API router.

Milestone 15: Complete end-to-end investigation execution pipeline.
Milestone 18: Added timeline endpoint.
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
from app.schemas.timeline import TimelineEventResponse, TimelineResponse
from app.services.exceptions import NotFoundError
from app.services.investigation_service import InvestigationService
from app.timeline.service import TimelineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigations", tags=["investigations"])


def get_investigation_service(db: Session = Depends(get_db)) -> InvestigationService:
    """FastAPI dependency that builds an InvestigationService per request."""
    return InvestigationService(db)


def get_timeline_service(db: Session = Depends(get_db)) -> TimelineService:
    """FastAPI dependency that builds a TimelineService per request."""
    return TimelineService(db)


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


@router.get(
    "/{investigation_id}/timeline",
    response_model=TimelineResponse,
    summary="Get investigation timeline",
)
def get_timeline(
    investigation_id: uuid.UUID,
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    timeline_service: TimelineService = Depends(get_timeline_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
) -> TimelineResponse:
    """
    Get timeline of events for an investigation.
    
    Extracts temporal events from normalized facts and returns them
    in chronological order. Supports filtering by entity and event type.
    """
    try:
        # Verify investigation exists
        investigation_service.get_investigation(investigation_id)
        
        # Get timeline events
        events = timeline_service.get_timeline(
            investigation_id=investigation_id,
            entity_id=entity_id,
            event_type=event_type,
        )
        
        return TimelineResponse(
            events=[
                TimelineEventResponse(
                    id=event.id,
                    investigation_id=event.investigation_id,
                    entity_id=event.entity_id,
                    occurred_at=event.occurred_at,
                    event_type=event.event_type,
                    title=event.title,
                    description=event.description,
                    connector=event.connector,
                    source_fact_id=event.source_fact_id,
                    confidence=event.confidence,
                )
                for event in events
            ],
            count=len(events),
        )
    
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(
            f"API: Timeline retrieval failed: {exc}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Timeline retrieval failed"
        ) from exc


def get_report_service(db: Session = Depends(get_db)):
    """FastAPI dependency for ReportService."""
    from app.services.report_service import ReportService
    return ReportService(db)


@router.post(
    "/{investigation_id}/report",
    status_code=status.HTTP_201_CREATED,
    summary="Generate investigation report",
)
def generate_report(
    investigation_id: uuid.UUID,
    report_service = Depends(get_report_service),
):
    """Generate PDF report for an investigation."""
    try:
        report = report_service.generate_report(investigation_id)
        return {
            "id": str(report.id),
            "investigation_id": str(report.investigation_id),
            "status": report.status.value,
            "file_size": report.file_size,
            "generated_at": report.generated_at.isoformat(),
        }
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generation failed"
        ) from exc


@router.get(
    "/{investigation_id}/report",
    summary="Download investigation report",
)
def download_report(
    investigation_id: uuid.UUID,
    report_service = Depends(get_report_service),
):
    """Download the latest PDF report for an investigation."""
    from fastapi.responses import Response
    
    try:
        report = report_service.get_latest_report(investigation_id)
        
        if report.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report is {report.status}, not available for download"
            )
        
        if not report.pdf_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report PDF content not found"
            )
        
        return Response(
            content=report.pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=investigation_{investigation_id}_report.pdf"
            }
        )
    
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Report download failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report download failed"
        ) from exc