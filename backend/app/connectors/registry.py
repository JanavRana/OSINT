"""
connectors/registry.py

The connector registry for the Multi-Source Connector Framework (M2,
Section 11.2 of MASTER_DESIGN.md).

This is the plugin boundary described by NFR3 and G9: adding a new
connector should require writing one new connector module plus a
registry entry — nothing else in the system changes. This module
defines that registration mechanism only. It contains no real
connectors and no knowledge of WHOIS/RDAP/crt.sh/Wayback/GitHub/
Gravatar specifically.

Two registration styles are supported, both self-contained (no need to
edit this file to add a connector):

    1. Decorator-based, at class-definition time:

        @registry.register
        class WhoisConnector(BaseConnector):
            name = "whois"
            supported_identifier_types = frozenset({IdentifierType.DOMAIN})
            ...

    2. Explicit, e.g. from an application startup/bootstrap module that
       imports connector packages and calls:

        registry.register(WhoisConnector)

Either way, connectors declare their own `supported_identifier_types`;
the registry only aggregates that information into a lookup table.
"""

from __future__ import annotations

from typing import Dict, List, Set, Type

from .base import BaseConnector
from .types import IdentifierType


class ConnectorRegistry:
    """
    Aggregates registered connector classes and indexes them by the
    identifier type(s) they declare support for (FR2.1).

    The registry does not instantiate connectors on registration; it
    stores classes and defers instantiation to the caller (e.g. the
    manager), keeping this module free of any assumptions about
    connector constructors (some may need config/credentials later).
    """

    def __init__(self) -> None:
        self._connectors_by_name: Dict[str, Type[BaseConnector]] = {}
        self._connectors_by_identifier_type: Dict[
            IdentifierType, List[Type[BaseConnector]]
        ] = {identifier_type: [] for identifier_type in IdentifierType}

    def register(self, connector_cls: Type[BaseConnector]) -> Type[BaseConnector]:
        """
        Register a connector class. Usable as a plain call or as a
        class decorator (it returns the class unchanged), e.g.:

            @registry.register
            class MyConnector(BaseConnector):
                ...

        Raises:
            ValueError: if the connector's `name` is missing/blank,
                declares no supported identifier types, or a different
                connector class is already registered under the same
                name (registration must be unambiguous).
        """
        if not connector_cls.name:
            raise ValueError(
                f"Connector class '{connector_cls.__name__}' must define "
                "a non-empty 'name'."
            )

        if not connector_cls.supported_identifier_types:
            raise ValueError(
                f"Connector '{connector_cls.name}' must declare at least "
                "one entry in 'supported_identifier_types'."
            )

        existing = self._connectors_by_name.get(connector_cls.name)
        if existing is not None and existing is not connector_cls:
            raise ValueError(
                f"A different connector class is already registered "
                f"under the name '{connector_cls.name}'."
            )

        self._connectors_by_name[connector_cls.name] = connector_cls

        for identifier_type in connector_cls.supported_identifier_types:
            bucket = self._connectors_by_identifier_type.setdefault(
                identifier_type, []
            )
            if connector_cls not in bucket:
                bucket.append(connector_cls)

        return connector_cls

    def unregister(self, name: str) -> None:
        """Remove a connector by name (primarily useful for tests)."""
        connector_cls = self._connectors_by_name.pop(name, None)
        if connector_cls is None:
            return
        for bucket in self._connectors_by_identifier_type.values():
            if connector_cls in bucket:
                bucket.remove(connector_cls)

    def get_connector(self, name: str) -> Type[BaseConnector]:
        """Look up a single registered connector class by name."""
        try:
            return self._connectors_by_name[name]
        except KeyError as exc:
            raise KeyError(f"No connector registered under name '{name}'.") from exc

    def get_connectors_for_identifier_type(
        self, identifier_type: IdentifierType
    ) -> List[Type[BaseConnector]]:
        """
        Return all connector classes registered as applicable to the
        given identifier type (FR2.1: "maintain a mapping of identifier
        type -> applicable connectors"). Returns an empty list if none
        are registered yet — this is expected and valid in v1, where
        connectors are added incrementally (Phase 1/2 of the roadmap).
        """
        return list(self._connectors_by_identifier_type.get(identifier_type, []))

    def all_connectors(self) -> List[Type[BaseConnector]]:
        """Return every registered connector class."""
        return list(self._connectors_by_name.values())

    def supported_identifier_types(self) -> Set[IdentifierType]:
        """Return the set of identifier types with at least one connector."""
        return {
            identifier_type
            for identifier_type, connectors in self._connectors_by_identifier_type.items()
            if connectors
        }


# Process-wide default registry. Concrete connector modules are expected
# to import this instance and register themselves against it (e.g. via
# the `@registry.register` decorator) at import time.
registry = ConnectorRegistry()