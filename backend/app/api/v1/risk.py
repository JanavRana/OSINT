"""
Risk scoring API endpoints.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.risk.scoring import RiskScorer
from app.services.investigation_service import InvestigationService
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk"])


def get_investigation_service(db: Session = Depends(get_db)) -> InvestigationService:
    return InvestigationService(db)


def get_risk_scorer() -> RiskScorer:
    return RiskScorer()


@router.get(
    "/{investigation_id}",
    summary="Get investigation risk score",
)
async def get_investigation_risk(
    investigation_id: UUID,
    investigation_service: InvestigationService = Depends(get_investigation_service),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
):
    """
    Calculate and return risk score for an investigation.
    """
    try:
        investigation_service.get_investigation(investigation_id)
        
        entities = await investigation_service.get_correlated_entities(investigation_id)
        
        if not entities:
            return {
                "investigation_id": str(investigation_id),
                "overall_score": 0.0,
                "risk_level": "low",
                "indicators": [],
                "factors": {}
            }
        
        risk_data = risk_scorer.calculate_investigation_risk(
            investigation_id,
            entities
        )
        
        return risk_data
    
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"Risk scoring failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk scoring failed"
        ) from exc
