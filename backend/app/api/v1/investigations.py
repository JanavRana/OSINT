"""
Investigation API router.

Milestone 15: Complete end-to-end investigation execution pipeline.
Milestone 18: Added timeline endpoint.
Auth: All endpoints require a valid JWT. Investigations are scoped per user.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors.types import Identifier
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.investigation import (
    ConnectorExecutionResult,
    ConnectorResultListResponse,
    ConnectorResultRead,
    ExecutionStatistics,
    IdentifierListResponse,
    IdentifierRead,
    InvestigationCreate,
    InvestigationExecuteRequest,
    InvestigationExecuteResponse,
    InvestigationList,
    InvestigationRead,
    SeedIdentifierSchema,
)
from app.schemas.timeline import TimelineEventResponse, TimelineResponse
from app.repositories.connector_result_repository import ConnectorResultRepository
from app.repositories.normalized_fact_repository import NormalizedFactRepository
from app.repositories.seed_identifier_repository import SeedIdentifierRepository
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


def _assert_owner(investigation, current_user: User) -> None:
    """Raise HTTP 403 if the investigation does not belong to the current user."""
    if investigation.user_id is not None and investigation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this investigation.",
        )


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new investigation",
)
def create_investigation(
    payload: InvestigationCreate,
    service: InvestigationService = Depends(get_investigation_service),
    current_user: User = Depends(get_current_user),
) -> InvestigationRead:
    seed_value = payload.seed_identifier.value if payload.seed_identifier else None
    seed_type = payload.seed_identifier.type.value if payload.seed_identifier else None
    investigation, seed = service.create_investigation(
        name=payload.name,
        seed_value=seed_value,
        seed_type=seed_type,
        user_id=current_user.id,
    )
    return InvestigationRead(
        id=investigation.id,
        name=investigation.name,
        status=investigation.status,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        seed_identifier=SeedIdentifierSchema(
            value=seed.value,
            type=seed.type,
        ) if seed else None,
    )


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
    current_user: User = Depends(get_current_user),
) -> InvestigationList:
    items, total = service.list_investigations(
        skip=skip, limit=limit, user_id=current_user.id
    )
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestigationRead:
    try:
        investigation = service.get_investigation(investigation_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    _assert_owner(investigation, current_user)

    # Attach seed identifier if one was saved at creation time
    seed_repo = SeedIdentifierRepository(db)
    seed = seed_repo.get_primary_by_investigation(investigation_id)

    logger.info(f"GET investigation_id={investigation_id}")
    logger.info(f"Seed object={seed}")

    if seed:
        logger.info(f"value={seed.value} type={seed.type}")

    return InvestigationRead(
        id=investigation.id,
        name=investigation.name,
        status=investigation.status,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        seed_identifier=SeedIdentifierSchema(
            value=seed.value,
            type=seed.type,
        ) if seed else None,
    )


@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an investigation",
)
def delete_investigation(
    investigation_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Permanently delete an investigation. Only the owner can delete their own cases."""
    try:
        service.delete_investigation(investigation_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


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
    current_user: User = Depends(get_current_user),
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
        # Verify ownership before executing
        investigation = service.get_investigation(investigation_id)
        _assert_owner(investigation, current_user)

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
    except HTTPException:
        raise
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
    "/{investigation_id}/identifiers",
    response_model=IdentifierListResponse,
    summary="List identifiers discovered for an investigation",
)
def list_identifiers(
    investigation_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdentifierListResponse:
    """
    List normalized facts as identifiers for an investigation.

    Maps fact_type to identifier type for the frontend.
    """
    try:
        investigation = service.get_investigation(investigation_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    _assert_owner(investigation, current_user)

    fact_repo = NormalizedFactRepository(db)
    facts = fact_repo.list_by_investigation(investigation_id)

    # Only fact types that represent real identifiers are surfaced.
    # WHOIS metadata (registrar, nameserver, expiration, org, location, etc.)
    # is intentionally excluded — it should not appear as domain identifiers.
    IDENTIFIER_FACT_TYPES: dict[str, str] = {
        "email": "email",
        "domain": "domain",
        "phone": "phone",
        "username": "username",
        "wallet_address": "wallet",
        "social_account": "social",
        "contact_info": "email",
        "profile_data": "username",
        "platform_account_found": "username",  # Username OSINT confirmed accounts
    }

    items: list[IdentifierRead] = []
    for f in facts:
        meta: dict = f.fact_metadata or {}

        # Handle Phone OSINT facts specially so carrier, region, line_type, timezone are exposed
        if f.connector_name == "phone":
            identifier_type = "phone"
            display_value = str(f.value)
            profile_url = None
            platform = "phone"

            if f.fact_type == "phone":
                platform_display_name = "Phone Number"
            elif f.fact_type == "location":
                platform_display_name = "Country / Region"
            elif f.fact_type == "contact_info" or meta.get("field") == "carrier":
                platform_display_name = "Carrier (Inferred)"
            elif meta.get("field") == "line_type":
                platform_display_name = "Line Type"
            elif meta.get("field") == "timezone":
                platform_display_name = "Timezone"
            else:
                platform_display_name = "Phone Metadata"

            items.append(
                IdentifierRead(
                    id=str(f.id),
                    type=identifier_type,
                    value=display_value,
                    confidence=f.confidence,
                    sources=1,
                    first_seen=f.created_at.isoformat() if f.created_at else "",
                    profile_url=profile_url,
                    platform=platform,
                    platform_display_name=platform_display_name,
                )
            )
            continue

        # Handle Crypto Wallet OSINT facts specially (Bitcoin, Ethereum, Solana)
        if f.connector_name in ("bitcoin", "ethereum", "solana"):
            identifier_type = "wallet"
            display_value = str(f.value)
            wallet_addr = meta.get("wallet_address") or f.value
            chain = meta.get("blockchain", f.connector_name)
            
            if chain == "ethereum":
                profile_url = f"https://etherscan.io/address/{wallet_addr}" if wallet_addr else None
                platform = "ethereum"
                chain_title = "Ethereum"
            elif chain == "solana":
                profile_url = f"https://solscan.io/account/{wallet_addr}" if wallet_addr else None
                platform = "solana"
                chain_title = "Solana"
            else:
                profile_url = f"https://blockstream.info/address/{wallet_addr}" if wallet_addr else None
                platform = "bitcoin"
                chain_title = "Bitcoin"

            data_type = meta.get("data_type")
            if f.fact_type == "wallet_address":
                addr_type = meta.get("address_type") or "address"
                platform_display_name = f"{chain_title} Wallet ({addr_type})"
            elif data_type == "balance":
                platform_display_name = f"Confirmed Balance ({chain_title})"
            elif data_type == "transaction_count":
                platform_display_name = f"Transaction Count ({chain_title})"
            elif data_type == "totals":
                platform_display_name = "Total Received / Sent"
            elif data_type == "timestamp":
                act = meta.get("activity_type", "activity").replace("_", " ").title()
                platform_display_name = f"{chain_title} Activity ({act})"
            elif data_type == "utxo":
                platform_display_name = "UTXO Data"
            elif data_type == "transaction":
                continue
            else:
                platform_display_name = f"{chain_title} Blockchain Data"

            items.append(
                IdentifierRead(
                    id=str(f.id),
                    type=identifier_type,
                    value=display_value,
                    confidence=f.confidence,
                    sources=1,
                    first_seen=f.created_at.isoformat() if f.created_at else "",
                    profile_url=profile_url,
                    platform=platform,
                    platform_display_name=platform_display_name,
                )
            )
            continue
        # Handle Truecaller facts specially so caller name, email, location are exposed cleanly
        if f.connector_name == "truecaller":
            display_value = str(f.value)
            profile_url = None
            platform = "truecaller"

            if f.fact_type == "profile_data":
                identifier_type = "username"
                platform_display_name = "Truecaller Name"
            elif f.fact_type == "email":
                identifier_type = "email"
                platform_display_name = "Truecaller Email"
            elif f.fact_type == "location":
                identifier_type = "phone"
                platform_display_name = "Truecaller Location"
            elif f.fact_type == "contact_info":
                identifier_type = "phone"
                platform_display_name = "Truecaller Carrier"
            else:
                identifier_type = "phone"
                platform_display_name = "Truecaller Info"

            items.append(
                IdentifierRead(
                    id=str(f.id),
                    type=identifier_type,
                    value=display_value,
                    confidence=f.confidence,
                    sources=1,
                    first_seen=f.created_at.isoformat() if f.created_at else "",
                    profile_url=profile_url,
                    platform=platform,
                    platform_display_name=platform_display_name,
                )
            )
            continue

        # Handle ip_geolocation facts: expose IP address, country, region, ISP, ASN, timezone
        if f.connector_name == "ip_geolocation":
            display_value = str(f.value)
            profile_url = None
            platform = "ip_geolocation"
            field = meta.get("field", "")
            ip_class = meta.get("ip_class", "")

            if field == "ip_address":
                if ip_class:
                    platform_display_name = f"IP Address ({ip_class})"
                else:
                    platform_display_name = "IP Address"
                identifier_type = "ip"
            elif field == "country":
                platform_display_name = "Country (Geolocation Estimate)"
                identifier_type = "ip"
            elif field == "region_city":
                platform_display_name = "Region / City (Geolocation Estimate)"
                identifier_type = "ip"
            elif field == "isp_org":
                platform_display_name = "ISP / Network Owner"
                identifier_type = "ip"
            elif field == "asn":
                platform_display_name = "ASN (Autonomous System)"
                identifier_type = "ip"
            elif field == "timezone":
                platform_display_name = "Timezone (Geolocation Estimate)"
                identifier_type = "ip"
            else:
                platform_display_name = "IP Geolocation Data"
                identifier_type = "ip"

            items.append(
                IdentifierRead(
                    id=str(f.id),
                    type=identifier_type,
                    value=display_value,
                    confidence=f.confidence,
                    sources=1,
                    first_seen=f.created_at.isoformat() if f.created_at else "",
                    profile_url=profile_url,
                    platform=platform,
                    platform_display_name=platform_display_name,
                )
            )
            continue

        # Handle reverse_dns facts: expose PTR hostnames discovered for IP addresses
        if f.connector_name == "reverse_dns" and f.fact_type == "domain":
            ip_addr = meta.get("ip_address", "")
            shodan_url = (
                f"https://www.shodan.io/host/{ip_addr}" if ip_addr else None
            )
            items.append(
                IdentifierRead(
                    id=str(f.id),
                    type="domain",
                    value=str(f.value),
                    confidence=f.confidence,
                    sources=1,
                    first_seen=f.created_at.isoformat() if f.created_at else "",
                    profile_url=shodan_url,
                    platform="reverse_dns",
                    platform_display_name="Reverse DNS (PTR Record)",
                )
            )
            continue

        identifier_type = IDENTIFIER_FACT_TYPES.get(f.fact_type)
        if identifier_type is None:
            # Registrar, nameserver, expiration, org, location, certificate,
            # archive_snapshot, image_hash, generic, domain_registration, etc.
            # are contextual metadata, not standalone identifiers — skip them.
            continue

        # Skip graph relationship edge facts to prevent duplicating primary profile_data facts
        if meta.get("graph_edge") is True or f.connector_name == "username_graph":
            continue

        # For username / profile_data facts the stored `value` is a JSON blob.
        # Extract the clean username and profile_url from metadata instead.
        if f.fact_type in ("profile_data", "social_account", "username", "platform_account_found"):
            display_value = meta.get("username") or str(f.value)
            profile_url: str | None = meta.get("profile_url") or None
            platform: str | None = meta.get("platform") or None
            platform_display_name: str | None = meta.get("platform_display_name") or None
            
            # Skip not-found results - they shouldn't become identifiers
            exists = meta.get("exists")
            if exists is False:
                continue
        else:
            display_value = str(f.value)
            profile_url = None
            platform = None
            platform_display_name = None

        items.append(
            IdentifierRead(
                id=str(f.id),
                type=identifier_type,
                value=display_value,
                confidence=f.confidence,
                sources=1,
                first_seen=f.created_at.isoformat() if f.created_at else "",
                profile_url=profile_url,
                platform=platform,
                platform_display_name=platform_display_name,
            )
        )

    return IdentifierListResponse(items=items, count=len(items))


@router.get(
    "/{investigation_id}/connectors",
    response_model=ConnectorResultListResponse,
    summary="List connector execution results for an investigation",
)
def list_connectors(
    investigation_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectorResultListResponse:
    """
    List connector execution results for an investigation.

    Returns a summary of each connector that was run, including hit count
    and execution status.
    """
    try:
        investigation = service.get_investigation(investigation_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    _assert_owner(investigation, current_user)

    result_repo = ConnectorResultRepository(db)
    results = result_repo.list_by_investigation(investigation_id)

    # Derive category from connector name
    connector_categories = {
        "whois": "Domain Intelligence",
        "rdap": "Domain Intelligence",
        "crtsh": "Certificate Transparency",
        "wayback": "Web Archives",
        "github": "Code & Social",
        "gravatar": "Profile Lookup",
        "phone": "Phone Intelligence",
        "truecaller": "Caller Intelligence",
        "ip_geolocation": "IP Intelligence",
        "reverse_dns": "IP Intelligence",
    }

    items = [
        ConnectorResultRead(
            id=str(r.id),
            name=r.connector_name,
            category=connector_categories.get(
                r.connector_name.lower(), "OSINT"
            ),
            status="success" if r.raw_response else "failed",
            hits=len(r.raw_response) if isinstance(r.raw_response, dict) else 0,
            runtime=r.created_at.strftime("%H:%M:%S") if r.created_at else "—",
        )
        for r in results
    ]

    return ConnectorResultListResponse(items=items, count=len(items))


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
    current_user: User = Depends(get_current_user),
) -> TimelineResponse:
    """
    Get timeline of events for an investigation.

    Extracts temporal events from normalized facts and returns them
    in chronological order. Supports filtering by entity and event type.
    """
    try:
        # Verify investigation exists and ownership
        investigation = investigation_service.get_investigation(investigation_id)
        _assert_owner(investigation, current_user)

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
    except HTTPException:
        raise
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


class ReportGeneratePayload(BaseModel):
    graph_image: str | None = None


@router.post(
    "/{investigation_id}/report",
    status_code=status.HTTP_201_CREATED,
    summary="Generate investigation report",
)
def generate_report(
    investigation_id: uuid.UUID,
    payload: ReportGeneratePayload | None = None,
    report_service=Depends(get_report_service),
    service: InvestigationService = Depends(get_investigation_service),
    current_user: User = Depends(get_current_user),
):
    """Generate PDF report for an investigation."""
    try:
        investigation = service.get_investigation(investigation_id)
        _assert_owner(investigation, current_user)
        graph_img = payload.graph_image if payload else None
        report = report_service.generate_report(investigation_id, graph_image_base64=graph_img)
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
    except HTTPException:
        raise
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
    report_service=Depends(get_report_service),
    service: InvestigationService = Depends(get_investigation_service),
    current_user: User = Depends(get_current_user),
):
    """Download the latest PDF report for an investigation."""
    from fastapi.responses import Response

    try:
        investigation = service.get_investigation(investigation_id)
        _assert_owner(investigation, current_user)
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