"""
Shared service-layer exceptions.

Kept generic (not Investigation-specific) so future service modules
(identifiers, entities, timeline, reports, etc.) can reuse the same
error vocabulary. API routers are responsible for translating these
into HTTP responses — the service layer itself never raises HTTPException.
"""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)