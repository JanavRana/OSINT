"""
FastAPI application entry point.

This wires together configuration and the API router. It intentionally
contains no business logic, models, or connector/service wiring — those
belong to other modules described in MASTER_DESIGN.md and are out of
scope for this skeleton.
"""

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
