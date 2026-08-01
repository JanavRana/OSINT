"""
ConnectorResult repository.

Encapsulates all direct SQLAlchemy access for the ConnectorResult entity.
This is the only place in the codebase that should issue queries
against the `connector_results` table.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.connector_result import ConnectorResult


class ConnectorResultRepository:
    """Data-access layer for the ConnectorResult entity."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        investigation_id: uuid.UUID,
        connector_name: str,
        identifier: str,
        raw_response: dict[str, Any],
    ) -> ConnectorResult:
        """Persist a new connector result and return the created row."""
        result = ConnectorResult(
            investigation_id=investigation_id,
            connector_name=connector_name,
            identifier=identifier,
            raw_response=raw_response,
        )
        self._db.add(result)
        self._db.commit()
        self._db.refresh(result)
        return result

    def list_by_investigation(
        self, investigation_id: uuid.UUID
    ) -> list[ConnectorResult]:
        """Return all connector results for a given investigation."""
        from sqlalchemy import select

        stmt = (
            select(ConnectorResult)
            .where(ConnectorResult.investigation_id == investigation_id)
            .order_by(ConnectorResult.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())
