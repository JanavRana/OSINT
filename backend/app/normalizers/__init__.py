"""
normalizers package

Data Normalization Engine (M3, Section 11.3 of MASTER_DESIGN.md).

This package defines the normalization framework that converts every
connector's raw output into the shared internal schema. It provides:
    - BaseNormalizer: abstract base class for all normalizers.
    - NormalizerRegistry: plugin registration for normalizers.
    - NormalizationManager: coordinates normalization across connectors.
    - Shared types: NormalizedFact, FactType, NormalizationResult, etc.

Concrete normalizers (whois/, rdap/, etc.) are not part of this
framework package — they import from here and register themselves.
"""

from .base import BaseNormalizer
from .manager import NormalizationManager, normalization_manager
from .registry import NormalizerRegistry, normalizer_registry
from .types import (
    FactType,
    NormalizationError,
    NormalizationResult,
    NormalizedFact,
)

# Import concrete normalizers to trigger auto-registration
# via @normalizer_registry.register decorator
from .whois import WhoisNormalizer  # noqa: F401
from .rdap import RdapNormalizer  # noqa: F401
from .dns import DnsNormalizer  # noqa: F401
from .reverse_dns import ReverseDnsNormalizer  # noqa: F401
from .ssl_certificate import SslCertificateNormalizer  # noqa: F401
from .phone import PhoneNormalizer  # noqa: F401
from .bitcoin import BitcoinNormalizer  # noqa: F401
from .ethereum import EthereumNormalizer  # noqa: F401
from .solana import SolanaNormalizer  # noqa: F401
from .truecaller import TruecallerNormalizer  # noqa: F401
from .ip import IpGeolocationNormalizer  # noqa: F401
from .mac import MacNormalizer  # noqa: F401
from .email import EmailOsintNormalizer  # noqa: F401
from .abstract_ip import AbstractIpNormalizer  # noqa: F401
from .abstract_phone import AbstractPhoneNormalizer  # noqa: F401
from .virustotal import VirusTotalNormalizer  # noqa: F401
from .github import GitHubNormalizer  # noqa: F401

__all__ = [
    "BaseNormalizer",
    "NormalizerRegistry",
    "normalizer_registry",
    "NormalizationManager",
    "normalization_manager",
    "FactType",
    "NormalizedFact",
    "NormalizationResult",
    "NormalizationError",
    "WhoisNormalizer",
    "RdapNormalizer",
    "DnsNormalizer",
    "ReverseDnsNormalizer",
    "SslCertificateNormalizer",
    "PhoneNormalizer",
    "BitcoinNormalizer",
    "EthereumNormalizer",
    "SolanaNormalizer",
    "TruecallerNormalizer",
    "IpGeolocationNormalizer",
    "MacNormalizer",
    "EmailOsintNormalizer",
    "AbstractIpNormalizer",
    "AbstractPhoneNormalizer",
    "VirusTotalNormalizer",
    "GitHubNormalizer",
]






