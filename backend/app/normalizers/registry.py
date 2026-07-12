"""
normalizers/registry.py

The normalizer registry for the Data Normalization Engine (M3, Section
11.3 of MASTER_DESIGN.md).

This is the plugin boundary for normalizers, parallel to the connector
registry. Adding a new normalizer should require writing one new
normalizer module plus a registry entry — nothing else in the system
changes (NFR3 applied to the normalization layer).

Two registration styles are supported:

    1. Decorator-based:
        @normalizer_registry.register
        class WhoisNormalizer(BaseNormalizer):
            connector_name = "whois"
            ...

    2. Explicit:
        normalizer_registry.register(WhoisNormalizer)

The registry maintains a connector_name → normalizer class mapping so
the normalization manager can look up the right normalizer for any
given connector's output.
"""

from __future__ import annotations

from typing import Dict, Type

from .base import BaseNormalizer


class NormalizerRegistry:
    """
    Aggregates registered normalizer classes and indexes them by the
    connector name they handle.
    
    The registry does not instantiate normalizers on registration; it
    stores classes and defers instantiation to the caller (the manager),
    keeping this module free of assumptions about normalizer constructors.
    """
    
    def __init__(self) -> None:
        self._normalizers_by_connector: Dict[str, Type[BaseNormalizer]] = {}
    
    def register(self, normalizer_cls: Type[BaseNormalizer]) -> Type[BaseNormalizer]:
        """
        Register a normalizer class. Usable as a plain call or as a
        class decorator (returns the class unchanged).
        
        Raises:
            ValueError: if the normalizer's `connector_name` is missing/blank,
                or a different normalizer class is already registered for
                the same connector name.
        """
        if not normalizer_cls.connector_name:
            raise ValueError(
                f"Normalizer class '{normalizer_cls.__name__}' must define "
                "a non-empty 'connector_name'."
            )
        
        existing = self._normalizers_by_connector.get(normalizer_cls.connector_name)
        if existing is not None and existing is not normalizer_cls:
            raise ValueError(
                f"A different normalizer class is already registered "
                f"for connector '{normalizer_cls.connector_name}'."
            )
        
        self._normalizers_by_connector[normalizer_cls.connector_name] = normalizer_cls
        return normalizer_cls
    
    def unregister(self, connector_name: str) -> None:
        """Remove a normalizer by connector name (primarily for tests)."""
        self._normalizers_by_connector.pop(connector_name, None)
    
    def get_normalizer(self, connector_name: str) -> Type[BaseNormalizer]:
        """
        Look up a normalizer class by connector name.
        
        Raises:
            KeyError: if no normalizer is registered for this connector.
                In v1, this is expected and valid during incremental
                development (not every connector has a normalizer yet).
        """
        try:
            return self._normalizers_by_connector[connector_name]
        except KeyError as exc:
            raise KeyError(
                f"No normalizer registered for connector '{connector_name}'."
            ) from exc
    
    def has_normalizer(self, connector_name: str) -> bool:
        """Check if a normalizer is registered for a connector."""
        return connector_name in self._normalizers_by_connector
    
    def all_normalizers(self) -> list[Type[BaseNormalizer]]:
        """Return every registered normalizer class."""
        return list(self._normalizers_by_connector.values())
    
    def supported_connectors(self) -> set[str]:
        """Return the set of connector names with a registered normalizer."""
        return set(self._normalizers_by_connector.keys())


# Process-wide default registry. Concrete normalizer modules are expected
# to import this instance and register themselves against it (e.g. via
# the `@normalizer_registry.register` decorator) at import time.
normalizer_registry = NormalizerRegistry()
