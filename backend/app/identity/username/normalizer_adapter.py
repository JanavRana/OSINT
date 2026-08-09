"""
Username platform normalizer adapter.

Bridges the identity username framework's DetectionOutcome payloads
(produced by UsernamePlatformExecutor) into NormalizationResult objects
that the investigation pipeline's normalization manager expects.

Registration approach: The normalizer manager is extended to support
prefix-based lookup (connector names like "username_platform:github")
via a subclass. All username platform envelopes share the same normalizer
logic — differences (profile URL, display name, etc.) are baked into the
raw_payload dict by the dispatcher.
"""

import logging
from datetime import datetime, timezone
from typing import Any, List

from app.normalizers.base import BaseNormalizer
from app.normalizers.types import FactType, NormalizedFact, NormalizationResult

logger = logging.getLogger(__name__)

# Prefix used by the dispatcher for all username platform connectors
USERNAME_PLATFORM_PREFIX = "username_platform:"


class UsernamePlatformNormalizer(BaseNormalizer):
    """
    Normalizer for username platform check results.

    Handles any connector whose name starts with "username_platform:".
    The raw_payload is a dict produced by the dispatcher containing:
        - platform_id: str
        - username: str
        - exists: True | False | "unknown"
        - http_status: Optional[int]
        - evidence_fields: dict
        - profile_url: str
        - platform_display_name: str
        - platform_category: str
        - platform_homepage: str
        - base_reliability: float
        - strategy_confidence_hint: float
        - duration_ms: Optional[float]
    """

    connector_name = USERNAME_PLATFORM_PREFIX  # Used for prefix matching

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert a username DetectionOutcome payload into normalized facts.

        Only creates facts for FOUND (exists=True) and NOT_FOUND (exists=False).
        Unknown/ambiguous results produce a fact with lower confidence.

        Args:
            raw_payload: Dict from dispatcher containing detection result

        Returns:
            List with 0 or 1 NormalizedFact
        """
        if not isinstance(raw_payload, dict):
            logger.warning(
                f"UsernamePlatformNormalizer: expected dict payload, got {type(raw_payload)}"
            )
            return []

        platform_id = raw_payload.get("platform_id", "unknown")
        username = raw_payload.get("username", "")
        exists = raw_payload.get("exists", "unknown")
        http_status = raw_payload.get("http_status")
        evidence_fields = raw_payload.get("evidence_fields", {})
        profile_url = raw_payload.get("profile_url", "")
        platform_display_name = raw_payload.get("platform_display_name", platform_id)
        platform_category = raw_payload.get("platform_category", "")
        platform_homepage = raw_payload.get("platform_homepage", "")
        base_reliability = raw_payload.get("base_reliability", 0.5)
        strategy_confidence = raw_payload.get("strategy_confidence_hint", 0.5)
        duration_ms = raw_payload.get("duration_ms")

        # Determine fact type based on existence
        if exists is True:
            fact_type = FactType.PROFILE_DATA
        elif exists is False:
            fact_type = FactType.GENERIC  # "not found" result
        else:
            # Unknown — lower confidence
            fact_type = FactType.GENERIC

        # Calculate confidence (simplified version of the identity normalizer logic)
        if exists is True:
            confidence = min(0.95, (base_reliability * 0.5) + (strategy_confidence * 0.5))
        elif exists is False and http_status == 404:
            confidence = max(0.85, base_reliability * 0.9)
        elif exists is False:
            confidence = base_reliability * 0.7
        else:
            # unknown
            confidence = min(0.3, base_reliability * 0.3)

        # Build the fact value and metadata
        fact_value = json_safe_str({
            "platform": platform_id,
            "platform_display_name": platform_display_name,
            "username": username,
            "exists": exists,
            "profile_url": profile_url if exists is True else None,
            "http_status": http_status,
        })

        metadata = {
            "platform_id": platform_id,
            "platform_display_name": platform_display_name,
            "platform_category": platform_category,
            "platform_homepage": platform_homepage,
            "username": username,
            "exists": exists,
            "profile_url": profile_url if exists is True else None,
            "source_url": profile_url if exists is True else None,
            "http_status": http_status,
            "evidence_fields": evidence_fields,
            "base_reliability": base_reliability,
            "strategy_confidence_hint": strategy_confidence,
            "duration_ms": duration_ms,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        fact = NormalizedFact(
            fact_type=fact_type,
            value=fact_value,
            source_connector=f"{USERNAME_PLATFORM_PREFIX}{platform_id}",
            confidence=max(0.0, min(1.0, confidence)),
            metadata=metadata,
            occurred_at=datetime.now(timezone.utc),
        )

        logger.debug(
            f"Normalized {platform_id}/{username}: exists={exists}, "
            f"confidence={confidence:.3f}, fact_type={fact_type}"
        )

        return [fact]


def json_safe_str(d: dict) -> str:
    """Convert a dict to a compact JSON-safe string representation for the 'value' field."""
    import json
    try:
        return json.dumps(d, default=str, separators=(',', ':'))
    except Exception:
        return str(d)
