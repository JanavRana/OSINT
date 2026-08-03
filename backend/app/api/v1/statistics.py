"""
Statistics API endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.statistics.service import StatisticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["statistics"])


def get_statistics_service(db: Session = Depends(get_db)) -> StatisticsService:
    return StatisticsService(db)


@router.get(
    "/overview",
    summary="Get overview statistics",
)
def get_overview_statistics(
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    High-level platform statistics.
    """
    try:
        return stats_service.get_overview_stats()
    except Exception as exc:
        logger.error(f"Overview stats failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Statistics retrieval failed"
        ) from exc


@router.get(
    "/connectors",
    summary="Get connector statistics",
)
def get_connector_statistics(
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Connector success rates and performance.
    """
    try:
        return {
            "connectors": stats_service.get_connector_stats()
        }
    except Exception as exc:
        logger.error(f"Connector stats failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connector statistics retrieval failed"
        ) from exc


@router.get(
    "/entities",
    summary="Get entity distribution",
)
def get_entity_statistics(
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Entity type distribution across investigations.
    """
    try:
        return {
            "entity_types": stats_service.get_entity_type_distribution()
        }
    except Exception as exc:
        logger.error(f"Entity stats failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entity statistics retrieval failed"
        ) from exc


@router.get(
    "/top/domains",
    summary="Get top domains",
)
def get_top_domains(
    limit: int = Query(10, ge=1, le=100),
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Most frequently appearing domains.
    """
    try:
        return {
            "domains": stats_service.get_top_domains(limit)
        }
    except Exception as exc:
        logger.error(f"Top domains failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Top domains retrieval failed"
        ) from exc


@router.get(
    "/top/registrars",
    summary="Get top registrars",
)
def get_top_registrars(
    limit: int = Query(10, ge=1, le=100),
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Most frequently appearing registrars.
    """
    try:
        return {
            "registrars": stats_service.get_top_registrars(limit)
        }
    except Exception as exc:
        logger.error(f"Top registrars failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Top registrars retrieval failed"
        ) from exc


@router.get(
    "/top/countries",
    summary="Get top countries",
)
def get_top_countries(
    limit: int = Query(10, ge=1, le=100),
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Most frequently appearing countries.
    """
    try:
        return {
            "countries": stats_service.get_top_countries(limit)
        }
    except Exception as exc:
        logger.error(f"Top countries failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Top countries retrieval failed"
        ) from exc


@router.get(
    "/durations",
    summary="Get investigation duration statistics",
)
def get_duration_statistics(
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Statistics on investigation execution time.
    """
    try:
        return stats_service.get_investigation_duration_stats()
    except Exception as exc:
        logger.error(f"Duration stats failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Duration statistics retrieval failed"
        ) from exc


@router.get(
    "/timeline",
    summary="Get investigation timeline statistics",
)
def get_timeline_statistics(
    days: int = Query(30, ge=1, le=365),
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Investigation creation timeline.
    """
    try:
        return {
            "timeline": stats_service.get_time_series_stats(days),
            "days": days
        }
    except Exception as exc:
        logger.error(f"Timeline stats failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Timeline statistics retrieval failed"
        ) from exc
