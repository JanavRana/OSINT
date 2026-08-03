"""
Global search API endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.search.service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@router.get(
    "",
    summary="Global search",
)
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    search_type: str = Query("all", regex="^(all|investigations|identifiers|facts)$"),
    limit: int = Query(50, ge=1, le=500),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Search across investigations, identifiers, and facts.
    """
    try:
        results = search_service.search(q, search_type, limit)
        return results
    except Exception as exc:
        logger.error(f"Search failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        ) from exc


@router.get(
    "/entity/{entity_type}",
    summary="Search by entity type",
)
def search_by_entity_type(
    entity_type: str,
    value: str = Query(None, description="Filter by value"),
    limit: int = Query(50, ge=1, le=500),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Search entities by type across all investigations.
    """
    try:
        results = search_service.search_by_entity_type(entity_type, value, limit)
        return {
            "entity_type": entity_type,
            "results": results,
            "count": len(results)
        }
    except Exception as exc:
        logger.error(f"Entity search failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entity search failed"
        ) from exc
