"""
Timeline service.

Extracts temporal events from normalized facts and provides timeline views.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.normalized_fact import NormalizedFact
from app.timeline.models import TimelineEvent

logger = logging.getLogger(__name__)


class TimelineService:
    """Service for generating and filtering timeline events from investigation facts."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_timeline(
        self,
        investigation_id: uuid.UUID,
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> list[TimelineEvent]:
        """
        Extract timeline events from normalized facts.

        Args:
            investigation_id: Investigation to generate timeline for
            entity_id: Optional filter by entity ID
            event_type: Optional filter by event type

        Returns:
            List of timeline events sorted chronologically
        """
        # Query normalized facts for the investigation
        query = self._db.query(NormalizedFact).filter(
            NormalizedFact.investigation_id == investigation_id
        )

        facts = query.all()

        # Extract events from facts
        events = []
        for fact in facts:
            extracted = self._extract_events_from_fact(fact)
            events.extend(extracted)

        # Apply filters
        if entity_id:
            events = [e for e in events if e.entity_id == entity_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Remove duplicates based on (occurred_at, event_type, title)
        seen = set()
        unique_events = []
        for event in events:
            key = (event.occurred_at, event.event_type, event.title)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)

        # Sort chronologically
        unique_events.sort(key=lambda e: e.occurred_at)

        return unique_events

    def _extract_events_from_fact(self, fact: NormalizedFact) -> list[TimelineEvent]:
        """
        Extract timeline events from a single normalized fact.

        Handles various fact types and their associated metadata to create events.
        """
        events = []
        metadata = fact.fact_metadata

        # WHOIS events
        if fact.connector_name == "whois":
            events.extend(self._extract_whois_events(fact, metadata))

        # RDAP events
        elif fact.connector_name == "rdap":
            events.extend(self._extract_rdap_events(fact, metadata))

        # crt.sh events
        elif fact.connector_name == "crt.sh":
            events.extend(self._extract_crtsh_events(fact, metadata))

        # Wayback events
        elif fact.connector_name == "wayback":
            events.extend(self._extract_wayback_events(fact, metadata))

        # Generic timestamp extraction for any future connectors
        else:
            events.extend(self._extract_generic_events(fact, metadata))

        return events

    def _extract_whois_events(
        self, fact: NormalizedFact, metadata: dict
    ) -> list[TimelineEvent]:
        """Extract events from WHOIS normalized facts."""
        events = []

        # Registration date
        if "registration_date" in metadata and metadata["registration_date"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["registration_date"]),
                    event_type="registration",
                    title=f"Domain {fact.value} registered",
                    description=f"Domain registration via WHOIS",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        # Expiration date
        if "expiration_date" in metadata and metadata["expiration_date"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["expiration_date"]),
                    event_type="expiration",
                    title=f"Domain {fact.value} expires",
                    description=f"Domain expiration date via WHOIS",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        # Updated date
        if "updated_date" in metadata and metadata["updated_date"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["updated_date"]),
                    event_type="updated",
                    title=f"Domain {fact.value} updated",
                    description=f"Domain record updated via WHOIS",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        return events

    def _extract_rdap_events(
        self, fact: NormalizedFact, metadata: dict
    ) -> list[TimelineEvent]:
        """Extract events from RDAP normalized facts."""
        events = []

        # Registration date
        if "registration_date" in metadata and metadata["registration_date"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["registration_date"]),
                    event_type="registration",
                    title=f"Domain {fact.value} registered",
                    description=f"Domain registration via RDAP",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        # Expiration date
        if "expiration_date" in metadata and metadata["expiration_date"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["expiration_date"]),
                    event_type="expiration",
                    title=f"Domain {fact.value} expires",
                    description=f"Domain expiration date via RDAP",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        # Last changed date
        if "last_changed" in metadata and metadata["last_changed"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["last_changed"]),
                    event_type="last_changed",
                    title=f"Domain {fact.value} last changed",
                    description=f"Domain record last changed via RDAP",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        return events

    def _extract_crtsh_events(
        self, fact: NormalizedFact, metadata: dict
    ) -> list[TimelineEvent]:
        """Extract events from crt.sh normalized facts."""
        events = []

        # Certificate issued
        if "not_before" in metadata and metadata["not_before"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["not_before"]),
                    event_type="certificate_issued",
                    title=f"Certificate issued for {fact.value}",
                    description=f"SSL/TLS certificate issued via crt.sh",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        # Certificate expires
        if "not_after" in metadata and metadata["not_after"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["not_after"]),
                    event_type="certificate_expires",
                    title=f"Certificate expires for {fact.value}",
                    description=f"SSL/TLS certificate expiration via crt.sh",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        return events

    def _extract_wayback_events(
        self, fact: NormalizedFact, metadata: dict
    ) -> list[TimelineEvent]:
        """Extract events from Wayback Machine normalized facts."""
        events = []

        # Archive snapshot
        if "timestamp" in metadata and metadata["timestamp"]:
            events.append(
                TimelineEvent(
                    investigation_id=fact.investigation_id,
                    entity_id=fact.value,
                    occurred_at=self._parse_timestamp(metadata["timestamp"]),
                    event_type="archive_snapshot",
                    title=f"Archive snapshot of {fact.value}",
                    description=f"Wayback Machine snapshot captured",
                    connector=fact.connector_name,
                    source_fact_id=fact.id,
                    confidence=fact.confidence,
                )
            )

        return events

    def _extract_generic_events(
        self, fact: NormalizedFact, metadata: dict
    ) -> list[TimelineEvent]:
        """
        Extract events from any fact with timestamp metadata.

        This allows future connectors to automatically participate in timeline
        generation if they include timestamp fields.
        """
        events = []

        # Common timestamp field names
        timestamp_fields = [
            "timestamp",
            "date",
            "created_at",
            "updated_at",
            "occurred_at",
            "event_time",
        ]

        for field in timestamp_fields:
            if field in metadata and metadata[field]:
                try:
                    events.append(
                        TimelineEvent(
                            investigation_id=fact.investigation_id,
                            entity_id=fact.value,
                            occurred_at=self._parse_timestamp(metadata[field]),
                            event_type=fact.fact_type,
                            title=f"{fact.fact_type}: {fact.value}",
                            description=f"Event from {fact.connector_name}",
                            connector=fact.connector_name,
                            source_fact_id=fact.id,
                            confidence=fact.confidence,
                        )
                    )
                except (ValueError, TypeError):
                    logger.debug(
                        f"Could not parse timestamp {field} from fact {fact.id}"
                    )

        return events

    def _parse_timestamp(self, value: any) -> datetime:
        """
        Parse timestamp from various formats.

        Handles:
        - datetime objects
        - ISO format strings
        - Common date strings
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        raise ValueError(f"Could not parse timestamp: {value}")
