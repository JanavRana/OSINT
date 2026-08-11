"""
connectors/

Multi-Source Connector Framework (M2, Section 11.2 of MASTER_DESIGN.md).

This package is the plugin boundary for OSINT source connectors
(WHOIS, RDAP, crt.sh, Wayback Machine, GitHub, Gravatar, and any future
source — see NFR3/G9). It contains only the framework:

    types.py     - shared vocabulary (IdentifierType, envelopes, statuses, errors)
    base.py      - BaseConnector abstract interface + shared execution plumbing
    registry.py  - plugin registration mapping identifier type -> connectors
    manager.py   - resolves + concurrently executes applicable connectors

No real connector (WHOIS, RDAP, etc.) is implemented in this package.
No HTTP requests are performed here. No normalization or correlation
logic lives here — see M3 (Normalization Engine) and M4 (Entity
Correlation Engine) elsewhere in the codebase.

Adding a new connector (the intended extension path):

    # connectors/whois/connector.py  (future work, not part of this package)
    from connectors.base import BaseConnector
    from connectors.registry import registry
    from connectors.types import IdentifierType

    @registry.register
    class WhoisConnector(BaseConnector):
        name = "whois"
        supported_identifier_types = frozenset({IdentifierType.DOMAIN})

        async def fetch(self, identifier):
            ...  # real WHOIS lookup logic goes here

No existing file in this package needs to change to add that connector.
"""

from .base import BaseConnector
from .manager import ConnectorManager
from .registry import ConnectorRegistry, registry
from .types import (
    ConnectorError,
    ConnectorExecutionError,
    ConnectorStatus,
    ConnectorTimeoutError,
    Identifier,
    IdentifierType,
    RawResponseEnvelope,
)

# Import connectors to trigger auto-registration via @registry.register decorator
from .whois import WhoisConnector  # noqa: F401
from .rdap import RdapConnector  # noqa: F401
from .dns import DnsConnector  # noqa: F401
from .reverse_dns import ReverseDnsConnector  # noqa: F401
from .ssl_certificate import SslCertificateConnector  # noqa: F401
from .phone import PhoneConnector  # noqa: F401
from .bitcoin import BitcoinConnector  # noqa: F401
from .ethereum import EthereumConnector  # noqa: F401
from .solana import SolanaConnector  # noqa: F401
from .truecaller import TruecallerConnector  # noqa: F401
from .ip import IpGeolocationConnector  # noqa: F401

__all__ = [
    "BaseConnector",
    "ConnectorManager",
    "ConnectorRegistry",
    "registry",
    "ConnectorError",
    "ConnectorExecutionError",
    "ConnectorStatus",
    "ConnectorTimeoutError",
    "Identifier",
    "IdentifierType",
    "RawResponseEnvelope",
    "WhoisConnector",
    "RdapConnector",
    "DnsConnector",
    "ReverseDnsConnector",
    "SslCertificateConnector",
    "PhoneConnector",
    "BitcoinConnector",
    "EthereumConnector",
    "SolanaConnector",
    "TruecallerConnector",
    "IpGeolocationConnector",
]