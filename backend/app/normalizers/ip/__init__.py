"""
normalizers/ip/

IP Geolocation normalizer package.

Exports:
    IpGeolocationNormalizer — converts IpGeolocationConnector raw payload
                               into normalized NormalizedFact instances.
"""

from .normalizer import IpGeolocationNormalizer

__all__ = ["IpGeolocationNormalizer"]
