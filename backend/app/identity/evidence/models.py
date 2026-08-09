"""
Data models for evidence and normalized facts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from ..confidence.engine import ConfidenceScore
from ..types import IdentifierType, VerificationMethod


@dataclass
class Evidence:
    """
    Provenance information for a fact.
    
    Tracks where and how a fact was obtained.
    """
    source_plugin_id: str
    verification_method: VerificationMethod
    observed_at: datetime
    raw_snapshot_ref: Optional[str] = None  # Reference to stored raw response
    execution_duration_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source_plugin_id": self.source_plugin_id,
            "verification_method": self.verification_method.value,
            "observed_at": self.observed_at.isoformat(),
            "raw_snapshot_ref": self.raw_snapshot_ref,
            "execution_duration_ms": self.execution_duration_ms,
        }


@dataclass
class NormalizedFact:
    """
    Normalized fact envelope - common structure for all identifier types.
    
    This is what gets stored in PostgreSQL and written to Neo4j.
    """
    id: UUID
    investigation_id: UUID
    identifier_type: IdentifierType
    identifier_value: str
    fact_type: str  # e.g., 'platform_account', 'mx_record', 'carrier_match'
    fact_payload: dict[str, Any]
    evidence: Evidence
    confidence: ConfidenceScore
    created_at: datetime = field(default_factory=datetime.utcnow)
    graph_entity_ref: Optional[str] = None  # Neo4j node ID once written
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "investigation_id": str(self.investigation_id),
            "identifier_type": self.identifier_type.value,
            "identifier_value": self.identifier_value,
            "fact_type": self.fact_type,
            "fact_payload": self.fact_payload,
            "evidence": self.evidence.to_dict(),
            "confidence": self.confidence.to_dict(),
            "created_at": self.created_at.isoformat(),
            "graph_entity_ref": self.graph_entity_ref,
        }


def create_username_platform_fact(
    investigation_id: UUID,
    username: str,
    platform_id: str,
    exists: bool,
    evidence_fields: dict[str, Any],
    evidence: Evidence,
    confidence: ConfidenceScore
) -> NormalizedFact:
    """
    Factory function to create a username platform fact.
    
    Args:
        investigation_id: Investigation ID
        username: Username checked
        platform_id: Platform identifier
        exists: Whether username exists on platform
        evidence_fields: Extracted fields (display_name, avatar, etc.)
        evidence: Provenance information
        confidence: Confidence score
        
    Returns:
        NormalizedFact instance
    """
    return NormalizedFact(
        id=uuid4(),
        investigation_id=investigation_id,
        identifier_type=IdentifierType.USERNAME,
        identifier_value=username,
        fact_type="platform_account",
        fact_payload={
            "platform_id": platform_id,
            "exists": exists,
            "evidence_fields": evidence_fields,
        },
        evidence=evidence,
        confidence=confidence,
    )


def create_email_fact(
    investigation_id: UUID,
    email: str,
    fact_type: str,
    payload: dict[str, Any],
    evidence: Evidence,
    confidence: ConfidenceScore
) -> NormalizedFact:
    """
    Factory function to create an email fact.
    
    Args:
        investigation_id: Investigation ID
        email: Email address
        fact_type: Type of fact (e.g., 'gravatar_profile', 'mx_record', 'breach_membership')
        payload: Fact-specific payload
        evidence: Provenance information
        confidence: Confidence score
        
    Returns:
        NormalizedFact instance
    """
    return NormalizedFact(
        id=uuid4(),
        investigation_id=investigation_id,
        identifier_type=IdentifierType.EMAIL,
        identifier_value=email,
        fact_type=fact_type,
        fact_payload=payload,
        evidence=evidence,
        confidence=confidence,
    )


def create_phone_fact(
    investigation_id: UUID,
    phone: str,
    fact_type: str,
    payload: dict[str, Any],
    evidence: Evidence,
    confidence: ConfidenceScore
) -> NormalizedFact:
    """
    Factory function to create a phone fact.
    
    Args:
        investigation_id: Investigation ID
        phone: Phone number
        fact_type: Type of fact (e.g., 'carrier_match', 'messaging_presence')
        payload: Fact-specific payload
        evidence: Provenance information
        confidence: Confidence score
        
    Returns:
        NormalizedFact instance
    """
    return NormalizedFact(
        id=uuid4(),
        investigation_id=investigation_id,
        identifier_type=IdentifierType.PHONE,
        identifier_value=phone,
        fact_type=fact_type,
        fact_payload=payload,
        evidence=evidence,
        confidence=confidence,
    )
