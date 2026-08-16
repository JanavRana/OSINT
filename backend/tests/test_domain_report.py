"""
Comprehensive test for domain report generation with real domain connectors and facts.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models.investigation import Investigation
from app.models.seed_identifier import SeedIdentifier
from app.models.report import ReportStatus
from app.services.report_service import ReportService
from app.services.investigation_service import InvestigationService
from app.connectors.types import Identifier, IdentifierType
from app.repositories.normalized_fact_repository import NormalizedFactRepository

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_domain_report_with_whois_raw_facts(db_session: Session):
    service = InvestigationService(db_session)
    inv, seed = service.create_investigation(
        name="Domain WHOIS Test",
        seed_value="example.com",
        seed_type="domain",
    )
    
    fact_repo = NormalizedFactRepository(db_session)
    
    # Simulate WHOIS & RDAP & DNS facts with special chars & long text that domains produce
    fact_repo.create_if_not_exists(
        investigation_id=inv.id,
        connector_name="whois",
        fact_type="domain_registration",
        value="<privacy_protected@whoisproxy.com> ['clientDeleteProhibited', 'clientTransferProhibited']",
        confidence=0.9,
        fact_metadata={"registrar": "MarkMonitor & Co <admin>"},
        occurred_at=datetime.now(timezone.utc),
    )
    
    fact_repo.create_if_not_exists(
        investigation_id=inv.id,
        connector_name="dns",
        fact_type="dns_record",
        value="A: 93.184.216.34 & 93.184.216.35",
        confidence=1.0,
        fact_metadata={"record_type": "A"},
        occurred_at=datetime.now(timezone.utc),
    )
    
    report_service = ReportService(db_session)
    report = report_service.generate_report(inv.id)
    assert report.status == ReportStatus.COMPLETED

def test_domain_report_with_all_domain_connectors(db_session: Session):
    service = InvestigationService(db_session)
    inv, seed = service.create_investigation(
        name="Real Domain Execution Test",
        seed_value="google.com",
        seed_type="domain",
    )
    
    identifier = Identifier(value="google.com", type=IdentifierType.DOMAIN)
    import asyncio
    res = asyncio.run(service.execute_investigation(inv.id, identifier))
    
    report_service = ReportService(db_session)
    report = report_service.generate_report(inv.id)
    assert report.status == ReportStatus.COMPLETED

def test_username_report_with_execution(db_session: Session):
    service = InvestigationService(db_session)
    inv, seed = service.create_investigation(
        name="Real Username Execution Test",
        seed_value="johndoe",
        seed_type="username",
    )
    
    identifier = Identifier(value="johndoe", type=IdentifierType.USERNAME)
    import asyncio
    res = asyncio.run(service.execute_investigation(inv.id, identifier))
    
    report_service = ReportService(db_session)
    report = report_service.generate_report(inv.id)
    assert report.status == ReportStatus.COMPLETED
