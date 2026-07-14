"""
reporting package

PDF Investigation Report generation (M8).
"""

from .report_generator import ReportGenerator
from .sections import (
    ConfidenceSection,
    ConnectorSection,
    CoverPage,
    EvidenceSection,
    ExecutiveSummary,
    InvestigationMetadata,
    RelationshipSection,
    SourcesSection,
    TimelineSection,
    UnifiedEntitiesSection,
)

__all__ = [
    "ReportGenerator",
    "CoverPage",
    "ExecutiveSummary",
    "InvestigationMetadata",
    "ConnectorSection",
    "UnifiedEntitiesSection",
    "RelationshipSection",
    "TimelineSection",
    "EvidenceSection",
    "SourcesSection",
    "ConfidenceSection",
]
