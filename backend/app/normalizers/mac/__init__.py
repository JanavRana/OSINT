"""
normalizers/mac/

MAC OSINT normalizer package.

Exports:
    MacNormalizer — converts MacOsintConnector raw payload into normalized facts.
"""

from .normalizer import MacNormalizer

__all__ = ["MacNormalizer"]
