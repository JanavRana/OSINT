"""
normalizers/types.py

Shared data types for the Data Normalization Engine (M3, Section 11.3
of MASTER_DESIGN.md).

This module defines the normalized fact schema that every connector's
raw output is mapped into, so that downstream modules (correlation,
graph, profile, timeline, report) only ever need to understand one
data shape (FR3.1, G3).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


class FactType(str, enum.Enum):
    """
    The taxonomy of normalized facts produced by connectors.
    
    Each fact type corresponds to a kind of evidence discoverable from
    OSINT sources. Normalizers map connector-specific raw output into
    one or more facts of these types.
    """
    
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    WALLET_ADDRESS = "wallet_address"
    IMAGE_HASH = "image_hash"
    
    DOMAIN_REGISTRATION = "domain_registration"
    CERTIFICATE = "certificate"
    ARCHIVE_SNAPSHOT = "archive_snapshot"
    SOCIAL_ACCOUNT = "social_account"
    PROFILE_DATA = "profile_data"
    
    CONTACT_INFO = "contact_info"
    ORGANIZATION = "organization"
    LOCATION = "location"
    
    GENERIC = "generic"


@dataclass
class NormalizedFact:
    """
    A single normalized fact extracted from a connector's raw response.
    
    This is the fundamental unit of evidence in the system (Section 11.3).
    Every downstream module (M4/M5/M6/M7/M8) operates on these facts,
    not on raw connector output.
    
    Fields:
        fact_type: The category of this fact.
        value: The primary value or a structured dict of attributes.
        occurred_at: Optional timestamp for timeline-eligible facts (FR7.1).
        source_connector: Which connector produced this fact (FR3.3, provenance).
        raw_reference_id: Identifier linking back to the raw response
            (FR3.2, NFR9: auditability).
        confidence: Optional confidence score (0.0-1.0). May be set by
            the normalizer or left for correlation to determine.
        metadata: Free-form extension point for fact-specific details
            that don't fit into the core fields.
    """
    
    fact_type: FactType
    value: Any
    source_connector: str
    occurred_at: Optional[datetime] = None
    raw_reference_id: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class NormalizationResult:
    """
    The result of normalizing a single connector's raw response.
    
    Contains:
        - A list of extracted normalized facts (may be empty if the
          raw response contained no usable data).
        - Metadata about the normalization process itself (timing,
          any non-fatal issues encountered).
    """
    
    facts: list[NormalizedFact]
    connector_name: str
    normalized_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class NormalizationError(Exception):
    """
    Raised when a normalizer encounters malformed or unparseable raw
    data that it cannot safely convert into normalized facts (FR3.3:
    "Reject/flag malformed or unparseable connector output").
    """
    
    def __init__(self, connector_name: str, message: str):
        self.connector_name = connector_name
        super().__init__(f"Normalization failed for '{connector_name}': {message}")
