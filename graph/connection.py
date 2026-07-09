"""
graph/connection.py

Connection management for the Neo4j graph query/visualization layer
(Section 14.2 of MASTER_DESIGN.md).

This module owns the lifecycle of the Neo4j driver (creation, session
acquisition, closing, and a basic health check). It intentionally
contains no node/relationship models, no Cypher queries beyond a
trivial connectivity check, and no correlation or business logic —
those belong to M4 (Entity Correlation Engine) and other modules per
Section 11 of MASTER_DESIGN.md.
"""

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jConnectionManager:
    """
    Manages a single Neo4j driver instance for the application.

    Usage:
        manager = Neo4jConnectionManager(Neo4jConfig.from_env())
        manager.connect()
        with manager.session() as session:
            ...  # session use is the responsibility of higher-level modules
        manager.close()

    This class is deliberately a thin wrapper around the official
    Neo4j Python driver — it does not define graph schema, queries,
    or domain logic.
    """

    def __init__(self, config: Neo4jConfig):
        self._config = config
        self._driver: Optional[Driver] = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def connect(self) -> None:
        """Initialize the Neo4j driver. Safe to call multiple times."""
        if self._driver is not None:
            logger.debug("Neo4j driver already initialized; skipping.")
            return

        logger.info("Connecting to Neo4j at %s", self._config.uri)
        self._driver = GraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password),
            max_connection_lifetime=self._config.max_connection_lifetime_seconds,
            max_connection_pool_size=self._config.max_connection_pool_size,
            connection_acquisition_timeout=(
                self._config.connection_acquisition_timeout_seconds
            ),
            connection_timeout=self._config.connection_timeout_seconds,
        )

    def close(self) -> None:
        """Close the Neo4j driver and release all pooled connections."""
        if self._driver is not None:
            logger.info("Closing Neo4j driver connection.")
            self._driver.close()
            self._driver = None

    def verify_connectivity(self) -> bool:
        """
        Basic health check that the configured Neo4j instance is reachable
        and credentials are valid. Returns True/False rather than raising,
        so callers (e.g., a startup health check) can decide how to react.
        """
        if self._driver is None:
            self.connect()

        try:
            self._driver.verify_connectivity()
            return True
        except (ServiceUnavailable, Neo4jError) as exc:
            logger.error("Neo4j connectivity check failed: %s", exc)
            return False

    @contextmanager
    def session(self, **kwargs) -> Iterator[Session]:
        """
        Yield a Neo4j session scoped to the configured database.

        Higher-level modules (not part of this infrastructure layer)
        are responsible for what they do with the session — running
        queries, managing transactions, etc.
        """
        if self._driver is None:
            self.connect()

        database = kwargs.pop("database", self._config.database)
        session = self._driver.session(database=database, **kwargs)
        try:
            yield session
        finally:
            session.close()

    def __enter__(self) -> "Neo4jConnectionManager":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


_manager: Optional[Neo4jConnectionManager] = None


def get_connection_manager() -> Neo4jConnectionManager:
    """
    Return a process-wide singleton Neo4jConnectionManager, built from
    environment configuration on first access.
    """
    global _manager
    if _manager is None:
        _manager = Neo4jConnectionManager(Neo4jConfig.from_env())
    return _manager
