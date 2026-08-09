"""
normalizers/manager.py

The normalization manager for the Data Normalization Engine (M3,
Section 11.3 of MASTER_DESIGN.md).

This module coordinates normalization across multiple connector
responses. It handles:
    - Looking up the appropriate normalizer for each connector.
    - Executing normalization while isolating failures.
    - Aggregating results across multiple connectors.

It contains no connector-specific parsing logic (that belongs in
concrete normalizers) and no database/persistence logic (that belongs
in M9).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..connectors.types import RawResponseEnvelope
from .registry import normalizer_registry
from .types import NormalizationError, NormalizationResult, NormalizedFact

# Prefix used by the username dispatcher for all platform connectors
_USERNAME_PLATFORM_PREFIX = "username_platform:"


class NormalizationManager:
    """
    Coordinates normalization of connector outputs.
    
    The manager is the entry point called by the orchestration layer
    (M1) or services layer. It uses the normalizer registry to find
    the appropriate normalizer for each connector's raw output, runs
    normalization, and handles errors gracefully (so one malformed
    response doesn't block normalization of others).
    """
    
    def __init__(self):
        """Initialize the manager with the default registry."""
        self.registry = normalizer_registry
    
    def normalize_envelope(
        self, 
        envelope: RawResponseEnvelope,
        raw_reference_id: str | None = None
    ) -> NormalizationResult | None:
        """
        Normalize a single RawResponseEnvelope.
        
        Args:
            envelope: The raw response envelope from a connector.
            raw_reference_id: Optional identifier linking to stored raw response.
        
        Returns:
            A NormalizationResult containing extracted facts, or None if:
                - The envelope indicates a failed/timed-out connector run
                  (no raw_payload to normalize).
                - No normalizer is registered for this connector yet
                  (expected during incremental development).
        
        Raises:
            NormalizationError: if normalization fails due to malformed data.
        """
        # Skip normalization if the connector itself failed
        if not envelope.succeeded:
            return None
        
        connector_name = envelope.connector_name
        
        # --- Prefix-based lookup for username platform connectors ---
        # Connector names like "username_platform:github" are routed to the
        # UsernamePlatformNormalizer without requiring individual registrations.
        if connector_name.startswith(_USERNAME_PLATFORM_PREFIX):
            normalizer_cls = self._get_username_platform_normalizer()
            if normalizer_cls is None:
                return None
            normalizer = normalizer_cls()
            return normalizer.run(envelope.raw_payload, raw_reference_id)
        
        # Check if a normalizer exists for this connector
        if not self.registry.has_normalizer(connector_name):
            return None
        
        # Get and instantiate the normalizer
        normalizer_cls = self.registry.get_normalizer(connector_name)
        normalizer = normalizer_cls()
        
        # Run normalization
        return normalizer.run(envelope.raw_payload, raw_reference_id)
    
    def _get_username_platform_normalizer(self):
        """
        Lazily import and return the UsernamePlatformNormalizer class.
        
        Lazy import avoids circular dependencies and keeps startup fast.
        Returns None if the adapter is unavailable (e.g., missing import).
        """
        try:
            from app.identity.username.normalizer_adapter import UsernamePlatformNormalizer
            return UsernamePlatformNormalizer
        except ImportError as e:
            import logging
            logging.getLogger(__name__).warning(
                f"UsernamePlatformNormalizer not available: {e}"
            )
            return None
    
    def normalize_batch(
        self,
        envelopes: List[RawResponseEnvelope],
        raw_reference_ids: Dict[str, str] | None = None
    ) -> List[NormalizationResult]:
        """
        Normalize multiple raw response envelopes.
        
        Processes each envelope independently, isolating failures so one
        bad normalization doesn't block others (FR2.4 applied to the
        normalization layer, NFR5).
        
        Args:
            envelopes: List of raw response envelopes to normalize.
            raw_reference_ids: Optional mapping of connector_name to
                raw_reference_id for provenance tracking.
        
        Returns:
            A list of NormalizationResult instances. Length may be less
            than input if some connectors failed or have no normalizer.
        """
        results = []
        ref_ids = raw_reference_ids or {}
        
        for envelope in envelopes:
            try:
                ref_id = ref_ids.get(envelope.connector_name)
                result = self.normalize_envelope(envelope, ref_id)
                if result is not None:
                    results.append(result)
            except NormalizationError:
                # Log error in production; for now, skip silently
                # (NFR5: resilience to partial failure)
                continue
            except Exception:
                # Catch-all for unexpected errors during normalization
                # (defensive programming, should not happen if normalizers
                # are well-written, but ensures one bad normalizer can't
                # crash the whole batch)
                continue
        
        return results
    
    def get_all_facts(
        self,
        normalization_results: List[NormalizationResult]
    ) -> List[NormalizedFact]:
        """
        Flatten multiple NormalizationResults into a single list of facts.
        
        Utility method for downstream consumers (correlation engine, etc.)
        that need a flat list of facts regardless of which connector
        produced them.
        """
        facts = []
        for result in normalization_results:
            facts.extend(result.facts)
        return facts


# Module-level singleton instance for convenience
normalization_manager = NormalizationManager()
