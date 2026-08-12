"""
normalizers/email/

Email OSINT normalizer package.

Transforms EmailOsintConnector raw output into normalized facts.
"""

from .normalizer import EmailOsintNormalizer

__all__ = [
    "EmailOsintNormalizer",
]
