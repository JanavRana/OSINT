"""
normalizers/base.py

The normalizer interface for the Data Normalization Engine (M3, Section
11.3 of MASTER_DESIGN.md).

This module defines the single contract every connector-specific
normalizer must implement. It contains NO actual normalization logic,
NO knowledge of specific connector formats (WHOIS, RDAP, etc.), and NO
database or correlation logic — only the abstract shape and the
execution wrapper that attaches provenance to every normalized fact.

Concrete normalizers (implemented elsewhere, e.g. normalizers/whois/)
are expected to:
    1. Subclass BaseNormalizer.
    2. Set `connector_name` to match the connector they normalize.
    3. Implement `normalize()` with source-specific parsing logic.
    4. Register themselves via the registry (see registry.py).
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, ClassVar, List

from .types import NormalizedFact, NormalizationResult


class BaseNormalizer(abc.ABC):
    """
    Abstract base class every connector-specific normalizer implements.
    
    A normalizer is responsible for taking a connector's raw response
    (whatever shape that source produces — JSON, plain text, XML, etc.)
    and converting it into zero or more NormalizedFact instances that
    follow the shared internal schema (FR3.1).
    
    The framework (this base class) handles provenance tracking and
    result envelope construction. Concrete normalizers only implement
    the connector-specific parsing logic in `normalize()`.
    """
    
    #: The name of the connector this normalizer handles. Must match
    #: the connector's `name` field exactly. Concrete subclasses must
    #: override this.
    connector_name: ClassVar[str] = ""
    
    @abc.abstractmethod
    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Parse a connector's raw response and extract normalized facts.
        
        This method contains no shared plumbing — it is pure
        source-specific parsing logic, implemented by concrete
        normalizers (not part of this framework task).
        
        Args:
            raw_payload: The untouched output from a connector's
                `fetch()` method. Shape is connector-specific.
        
        Returns:
            A list of NormalizedFact instances. May be empty if the
            raw data contains no usable information (e.g., a WHOIS
            lookup for an unregistered domain).
        
        Raises:
            NormalizationError: if the raw_payload is malformed in a
                way the normalizer cannot safely handle (FR3.3).
        """
        raise NotImplementedError
    
    def run(self, raw_payload: Any, raw_reference_id: str | None = None) -> NormalizationResult:
        """
        Execute normalization and attach provenance metadata.
        
        This is the entry point the normalization manager calls.
        It delegates to `normalize()` for the actual parsing work,
        then enriches each resulting fact with connector name and
        raw reference (FR3.3: "record, for every normalized fact,
        which connector and which raw response produced it").
        
        Args:
            raw_payload: The connector's raw output.
            raw_reference_id: Optional identifier linking back to the
                stored raw response (for evidence traceability).
        
        Returns:
            A NormalizationResult containing the list of facts and
            metadata about the normalization process.
        """
        facts = self.normalize(raw_payload)
        
        # Attach provenance to every fact
        for fact in facts:
            if fact.source_connector != self.connector_name:
                fact.source_connector = self.connector_name
            if raw_reference_id and not fact.raw_reference_id:
                fact.raw_reference_id = raw_reference_id
        
        return NormalizationResult(
            facts=facts,
            connector_name=self.connector_name,
            normalized_at=datetime.now(timezone.utc),
        )
