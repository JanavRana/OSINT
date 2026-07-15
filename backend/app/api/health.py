from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from ..core.config import get_settings
from ..db.session import engine

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "unknown",
            "neo4j": "not_configured"
        }
    }
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
    
    return health_status
