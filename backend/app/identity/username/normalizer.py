"""
Normalization for username platform results.

Converts DetectionOutcome from platforms into NormalizedFact instances
for the investigation graph and timeline.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from uuid import uuid4

from ..confidence.engine import ConfidenceFactors, ConfidenceScore
from ..evidence.models import Evidence, NormalizedFact
from ..plugin_base import DetectionOutcome, RawResult
from ..types import IdentifierType, VerificationMethod

logger = logging.getLogger(__name__)


def normalize_username_result(
    raw_result: RawResult,
    investigation_id: UUID,
    definition: Any = None
) -> Optional[NormalizedFact]:
    """
    Normalize a username platform check result into a NormalizedFact.
    
    Only creates facts for confirmed accounts (exists=True).
    Not-found (exists=False) and unknown results are not persisted as identifiers.
    
    Args:
        raw_result: Raw result from platform execution
        investigation_id: UUID of the investigation
        definition: Optional PlatformDefinition for additional context
        
    Returns:
        NormalizedFact instance for confirmed accounts, or None otherwise
    """
    # Ensure payload is a DetectionOutcome
    if not isinstance(raw_result.payload, DetectionOutcome):
        logger.error(
            f"Expected DetectionOutcome payload, got {type(raw_result.payload)}"
        )
        return None
    
    outcome = raw_result.payload
    
    # Don't create facts for failed checks
    if not raw_result.success:
        logger.debug(
            f"Skipping normalization for failed result: {raw_result.plugin_id}"
        )
        return None
    
    # IMPORTANT: Only create identifiers for confirmed accounts
    # Don't persist not-found or unknown results as identifiers
    if outcome.exists is not True:
        logger.debug(
            f"Skipping identifier creation for {raw_result.plugin_id}/{raw_result.identifier_value}: "
            f"exists={outcome.exists}"
        )
        return None
    
    # Build profile URL only for confirmed accounts
    profile_url = _build_profile_url(
        raw_result.plugin_id,
        raw_result.identifier_value,
        definition
    )
    
    # Build fact payload
    fact_payload = {
        "platform": raw_result.plugin_id,
        "username": raw_result.identifier_value,
        "exists": outcome.exists,
        "profile_url": profile_url,
        "http_status": outcome.http_status,
        "evidence_fields": outcome.evidence_fields,
        "checked_at": raw_result.timestamp.isoformat(),
    }
    
    # Add definition metadata if available
    if definition:
        fact_payload["platform_display_name"] = definition.display_name
        fact_payload["platform_category"] = definition.category.value
        fact_payload["platform_homepage"] = str(definition.homepage)
    
    # Build evidence
    evidence = Evidence(
        source_plugin_id=raw_result.plugin_id,
        verification_method=_get_verification_method(definition),
        raw_snapshot_ref=raw_result.raw_snapshot_ref or "",
        observed_at=raw_result.timestamp,
        execution_duration_ms=raw_result.duration_ms
    )
    
    # Calculate confidence score
    confidence = _calculate_confidence(
        outcome,
        definition,
        raw_result
    )
    
    # Fact type for confirmed account
    fact_type = "platform_account_found"
    
    # Create normalized fact
    normalized_fact = NormalizedFact(
        id=uuid4(),
        investigation_id=investigation_id,
        identifier_type=IdentifierType.USERNAME,
        identifier_value=raw_result.identifier_value,
        fact_type=fact_type,
        fact_payload=fact_payload,
        evidence=evidence,
        confidence=confidence
    )
    
    logger.debug(
        f"Normalized {raw_result.plugin_id} result for username "
        f"'{raw_result.identifier_value}': exists={outcome.exists}, "
        f"confidence={confidence.value:.3f}"
    )
    
    return normalized_fact


def _build_profile_url(
    plugin_id: str,
    username: str,
    definition: Any
) -> str:
    """Build profile URL from definition template."""
    if definition and hasattr(definition, 'get_profile_url'):
        return definition.get_profile_url(username)
    
    # Fallback for common patterns
    return f"https://example.com/{username}"


def _get_verification_method(definition: Any) -> VerificationMethod:
    """Extract verification method from platform definition."""
    if definition and hasattr(definition, 'confidence_rules'):
        return definition.confidence_rules.verification_method
    
    # Default fallback
    return VerificationMethod.HTML_SCRAPE


def _calculate_confidence(
    outcome: DetectionOutcome,
    definition: Any,
    raw_result: RawResult
) -> ConfidenceScore:
    """
    Calculate confidence score for a username detection.
    
    This is a simplified version. The full confidence engine
    would incorporate multiple factors.
    
    Args:
        outcome: Detection outcome
        definition: Platform definition
        raw_result: Raw result with timing info
        
    Returns:
        ConfidenceScore object
    """
    # Start with strategy hint
    strategy_confidence = outcome.strategy_confidence_hint
    
    # Get platform reliability if available
    if definition and hasattr(definition, 'confidence_rules'):
        source_reliability = definition.confidence_rules.base_reliability
    else:
        source_reliability = 0.5  # Default medium reliability
    
    # Verification method score
    verification_method_score = strategy_confidence
    
    # Corroboration score based on evidence fields
    corroboration_score = 0.5  # Base
    if outcome.evidence_fields:
        evidence_count = len(outcome.evidence_fields)
        # Increase with more fields (max 1.0)
        corroboration_score = min(0.5 + (evidence_count * 0.1), 1.0)
    
    # Freshness score (always fresh for immediate checks)
    freshness_score = 1.0
    
    # Historical success score (would come from metrics in production)
    historical_success_score = 0.9
    
    # Calculate weighted average
    # Weights from confidence engine design
    weights = {
        "source_reliability": 0.3,
        "verification_method": 0.3,
        "corroboration": 0.2,
        "freshness": 0.1,
        "historical_success": 0.1,
    }
    
    confidence_value = (
        weights["source_reliability"] * source_reliability +
        weights["verification_method"] * verification_method_score +
        weights["corroboration"] * corroboration_score +
        weights["freshness"] * freshness_score +
        weights["historical_success"] * historical_success_score
    )
    
    # Adjust for existence status
    if outcome.exists == "unknown":
        # Unknown results have lower confidence
        confidence_value *= 0.5
    elif outcome.exists is False:
        # Not found can be high confidence if we got explicit 404
        if outcome.http_status == 404:
            confidence_value = max(confidence_value, 0.85)
    
    # Ensure valid range
    confidence_value = max(0.0, min(1.0, confidence_value))
    
    # Build factors object
    factors = ConfidenceFactors(
        source_reliability=source_reliability,
        verification_method=verification_method_score,
        corroboration=corroboration_score,
        freshness=freshness_score,
        historical_success=historical_success_score,
    )
    
    return ConfidenceScore(
        value=confidence_value,
        factors=factors,
        weights_version="1.0"
    )


def batch_normalize_username_results(
    raw_results: list[RawResult],
    investigation_id: UUID,
    definitions_by_id: Optional[dict[str, Any]] = None
) -> list[NormalizedFact]:
    """
    Normalize a batch of username results.
    
    Args:
        raw_results: List of raw results
        investigation_id: Investigation UUID
        definitions_by_id: Optional dict mapping plugin_id -> PlatformDefinition
        
    Returns:
        List of normalized facts (excludes any that failed normalization)
    """
    definitions_by_id = definitions_by_id or {}
    normalized_facts = []
    
    for raw_result in raw_results:
        definition = definitions_by_id.get(raw_result.plugin_id)
        
        fact = normalize_username_result(
            raw_result,
            investigation_id,
            definition
        )
        
        if fact:
            normalized_facts.append(fact)
    
    logger.info(
        f"Normalized {len(normalized_facts)}/{len(raw_results)} username results"
    )
    
    return normalized_facts
