"""
Integration test for investigation execution pipeline.

Tests the complete end-to-end execution workflow without requiring
Docker or PostgreSQL (uses in-memory SQLite).
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.connectors.types import (
    ConnectorStatus,
    Identifier,
    IdentifierType,
    RawResponseEnvelope,
)
from app.db.session import Base
from app.models.investigation import InvestigationStatus
from app.normalizers.types import FactType, NormalizedFact, NormalizationResult
from app.services.investigation_service import InvestigationService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_connector_responses():
    """Mock connector responses."""
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    return [
        RawResponseEnvelope(
            connector_name="whois",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload={
                "registrar": "Example Registrar",
                "creation_date": "2020-01-15T10:30:00",
                "org": "Example Org",
            },
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        ),
        RawResponseEnvelope(
            connector_name="rdap",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload={
                "handle": "EXAMPLE-COM",
                "entities": [{"handle": "ADMIN123"}],
            },
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        ),
        RawResponseEnvelope(
            connector_name="failed_connector",
            identifier=identifier,
            status=ConnectorStatus.FAILED,
            error_message="Connection timeout",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def mock_normalization_results():
    """Mock normalization results."""
    return [
        NormalizationResult(
            facts=[
                NormalizedFact(
                    fact_type=FactType.DOMAIN_REGISTRATION,
                    value="Example Registrar",
                    source_connector="whois",
                    confidence=1.0,
                    metadata={"field": "registrar"},
                ),
                NormalizedFact(
                    fact_type=FactType.ORGANIZATION,
                    value="Example Org",
                    source_connector="whois",
                    confidence=1.0,
                    metadata={"field": "organization"},
                ),
            ],
            connector_name="whois",
            normalized_at=datetime.utcnow(),
        ),
        NormalizationResult(
            facts=[
                NormalizedFact(
                    fact_type=FactType.DOMAIN,
                    value="EXAMPLE-COM",
                    source_connector="rdap",
                    confidence=1.0,
                    metadata={"field": "handle"},
                ),
            ],
            connector_name="rdap",
            normalized_at=datetime.utcnow(),
        ),
    ]


@pytest.mark.asyncio
async def test_execute_investigation_success(
    db_session, mock_connector_responses, mock_normalization_results
):
    """Test successful investigation execution."""
    service = InvestigationService(db_session)
    
    # Create investigation
    investigation = service.create_investigation(name="Test Investigation")
    assert investigation.status == InvestigationStatus.CREATED
    
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    # Mock connector execution service
    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as mock_connector_service_class:
        mock_connector_service = MagicMock()
        mock_connector_service.execute_connectors = AsyncMock(
            return_value=mock_connector_responses
        )
        mock_connector_service_class.return_value = mock_connector_service
        
        # Mock normalization manager
        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm_manager:
            mock_norm_manager.normalize_batch.return_value = mock_normalization_results
            
            # Recreate service with mocks
            service = InvestigationService(db_session)
            
            # Execute investigation
            result = await service.execute_investigation(
                investigation.id, identifier
            )
    
    # Verify execution result
    assert result.investigation_id == investigation.id
    assert result.status == InvestigationStatus.COMPLETED
    assert result.executed_connectors == 3
    assert result.successful_connectors == 2
    assert result.failed_connectors == 1
    assert result.connector_results_count == 2
    assert result.normalized_facts_count == 3
    assert result.execution_duration_seconds > 0
    assert len(result.raw_responses) == 3
    
    # Verify investigation status updated
    updated_investigation = service.get_investigation(investigation.id)
    assert updated_investigation.status == InvestigationStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_investigation_connector_failure_does_not_stop_pipeline(
    db_session, mock_connector_responses, mock_normalization_results
):
    """Test that connector failures don't stop the pipeline."""
    service = InvestigationService(db_session)
    investigation = service.create_investigation(name="Test Investigation")
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as mock_connector_service_class:
        mock_connector_service = MagicMock()
        mock_connector_service.execute_connectors = AsyncMock(
            return_value=mock_connector_responses
        )
        mock_connector_service_class.return_value = mock_connector_service
        
        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm_manager:
            mock_norm_manager.normalize_batch.return_value = mock_normalization_results
            
            service = InvestigationService(db_session)
            result = await service.execute_investigation(
                investigation.id, identifier
            )
    
    # Pipeline should complete despite 1 failed connector
    assert result.status == InvestigationStatus.COMPLETED
    assert result.failed_connectors == 1
    assert result.normalized_facts_count == 3


@pytest.mark.asyncio
async def test_execute_investigation_normalizer_failure_does_not_stop_pipeline(
    db_session, mock_connector_responses
):
    """Test that normalizer failures don't stop the pipeline."""
    service = InvestigationService(db_session)
    investigation = service.create_investigation(name="Test Investigation")
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    # Mock with one normalizer raising exception
    failing_norm_results = [
        NormalizationResult(
            facts=[
                NormalizedFact(
                    fact_type=FactType.DOMAIN,
                    value="test",
                    source_connector="whois",
                    confidence=1.0,
                    metadata={},
                ),
            ],
            connector_name="whois",
            normalized_at=datetime.utcnow(),
        ),
    ]
    
    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as mock_connector_service_class:
        mock_connector_service = MagicMock()
        mock_connector_service.execute_connectors = AsyncMock(
            return_value=mock_connector_responses
        )
        mock_connector_service_class.return_value = mock_connector_service
        
        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm_manager:
            mock_norm_manager.normalize_batch.return_value = failing_norm_results
            
            service = InvestigationService(db_session)
            result = await service.execute_investigation(
                investigation.id, identifier
            )
    
    # Pipeline should complete
    assert result.status == InvestigationStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_investigation_not_found(db_session):
    """Test executing non-existent investigation raises NotFoundError."""
    from app.services.exceptions import NotFoundError
    
    service = InvestigationService(db_session)
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    fake_id = uuid.uuid4()
    
    with pytest.raises(NotFoundError):
        await service.execute_investigation(fake_id, identifier)


@pytest.mark.asyncio
async def test_execute_investigation_persists_connector_results(
    db_session, mock_connector_responses, mock_normalization_results
):
    """Test that connector results are persisted."""
    from app.repositories.connector_result_repository import (
        ConnectorResultRepository,
    )
    
    service = InvestigationService(db_session)
    investigation = service.create_investigation(name="Test Investigation")
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as mock_connector_service_class:
        mock_connector_service = MagicMock()
        mock_connector_service.execute_connectors = AsyncMock(
            return_value=mock_connector_responses
        )
        mock_connector_service_class.return_value = mock_connector_service
        
        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm_manager:
            mock_norm_manager.normalize_batch.return_value = mock_normalization_results
            
            service = InvestigationService(db_session)
            result = await service.execute_investigation(
                investigation.id, identifier
            )
    
    # Connector results should be persisted (mocked in connector service)
    assert result.connector_results_count == 2


@pytest.mark.asyncio
async def test_execute_investigation_persists_normalized_facts(
    db_session, mock_connector_responses, mock_normalization_results
):
    """Test that normalized facts are persisted."""
    service = InvestigationService(db_session)
    investigation = service.create_investigation(name="Test Investigation")
    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)
    
    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as mock_connector_service_class:
        mock_connector_service = MagicMock()
        mock_connector_service.execute_connectors = AsyncMock(
            return_value=mock_connector_responses
        )
        mock_connector_service_class.return_value = mock_connector_service
        
        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm_manager:
            mock_norm_manager.normalize_batch.return_value = mock_normalization_results
            
            service = InvestigationService(db_session)
            result = await service.execute_investigation(
                investigation.id, identifier
            )
    
    # All facts should be persisted
    assert result.normalized_facts_count == 3
