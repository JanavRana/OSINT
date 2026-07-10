"""
SQLAlchemy engine and session management.

This module defines ONLY the database connection plumbing (engine,
session factory, declarative base, and a FastAPI dependency for
obtaining a session). It does not define any ORM models — those belong
to a later module (M9 — Investigation & Persistence Layer) that is out
of scope for this skeleton.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


class Base(DeclarativeBase):
    """Shared declarative base for all future ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
