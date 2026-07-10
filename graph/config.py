"""
graph/config.py

Configuration for the Neo4j graph query/visualization layer (Section 14.2
of MASTER_DESIGN.md). This module is intentionally limited to reading
connection settings from environment variables — it defines no schema,
no queries, and no business logic.

Per NFR10 (Reasonable security hygiene), credentials are never
hard-coded and must be supplied via environment configuration
(directly, or via a .env file loaded by the process/deployment tooling).
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jConfig:
    """Immutable Neo4j connection configuration."""

    uri: str
    user: str
    password: str
    database: str

    # Connection pool / driver behavior tunables. Conservative defaults
    # suitable for a single-machine, hackathon-scale deployment (NFR6, NFR8).
    max_connection_lifetime_seconds: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout_seconds: int = 60
    connection_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """
        Build a Neo4jConfig from environment variables.

        Recognized variables:
            NEO4J_URI       (default: bolt://localhost:7687)
            NEO4J_USER      (default: neo4j)
            NEO4J_PASSWORD  (required — no insecure default)
            NEO4J_DATABASE  (default: neo4j)

            NEO4J_MAX_CONNECTION_LIFETIME_SECONDS
            NEO4J_MAX_CONNECTION_POOL_SIZE
            NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS
            NEO4J_CONNECTION_TIMEOUT_SECONDS
        """
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable is required and must "
                "not be hard-coded (see NFR10 in MASTER_DESIGN.md)."
            )

        return cls(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=password,
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
            max_connection_lifetime_seconds=int(
                os.environ.get("NEO4J_MAX_CONNECTION_LIFETIME_SECONDS", 3600)
            ),
            max_connection_pool_size=int(
                os.environ.get("NEO4J_MAX_CONNECTION_POOL_SIZE", 50)
            ),
            connection_acquisition_timeout_seconds=int(
                os.environ.get(
                    "NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS", 60
                )
            ),
            connection_timeout_seconds=int(
                os.environ.get("NEO4J_CONNECTION_TIMEOUT_SECONDS", 30)
            ),
        )
