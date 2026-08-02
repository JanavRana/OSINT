"""
connectors/ssl_certificate/connector.py

SSL Certificate connector implementation using ssl and socket libraries.

This connector:
    1. Subclasses BaseConnector
    2. Registers itself automatically via the @registry.register decorator
    3. Accepts DOMAIN identifiers
    4. Retrieves SSL/TLS certificate information from HTTPS servers
    5. Returns RAW certificate data without normalization
    6. Does NOT store data, access database, or call FastAPI
"""

from __future__ import annotations

import asyncio
import ssl
from datetime import datetime
from typing import Any, ClassVar, FrozenSet

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType


@registry.register
class SslCertificateConnector(BaseConnector):
    """
    SSL Certificate lookup connector for domain identifiers.

    Retrieves SSL/TLS certificate information from HTTPS servers on port 443.
    Returns the raw certificate data for downstream normalization (M3).
    """

    name: ClassVar[str] = "ssl_certificate"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.DOMAIN}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> dict[str, Any]:
        """
        Retrieve SSL certificate for the given domain identifier.

        Args:
            identifier: A domain identifier (e.g., value="example.com")

        Returns:
            A JSON-serializable dictionary containing SSL certificate data
            including subject, issuer, validity dates, SANs, etc.

        Raises:
            ssl.SSLError: If SSL connection fails
            Exception: Any other error during certificate retrieval
        """
        domain = identifier.value
        port = 443  # Standard HTTPS port

        result: dict[str, Any] = {
            "domain": domain,
            "port": port,
        }

        try:
            # Create SSL context
            context = ssl.create_default_context()
            # Don't verify certificates - we want to retrieve cert data even if invalid
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Connect and retrieve certificate
            # Run the blocking socket operation in a thread pool
            loop = asyncio.get_event_loop()
            cert_dict = await loop.run_in_executor(
                None, self._get_certificate_sync, domain, port, context
            )

            if cert_dict:
                result["certificate"] = self._parse_certificate(cert_dict)
            else:
                result["error"] = f"No certificate retrieved for {domain}:{port}"

        except ssl.SSLError as e:
            result["error"] = f"SSL error: {e}"
        except OSError as e:
            result["error"] = f"Connection error: {e}"
        except Exception as e:
            result["error"] = f"Certificate retrieval failed: {e}"

        return result

    def _get_certificate_sync(
        self, domain: str, port: int, context: ssl.SSLContext
    ) -> dict[str, Any] | None:
        """
        Synchronous helper to retrieve certificate using socket.

        This runs in a thread pool executor to avoid blocking the event loop.
        """
        import socket

        try:
            with socket.create_connection((domain, port), timeout=self.timeout_seconds) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    return ssock.getpeercert()
        except Exception:
            return None

    def _parse_certificate(self, cert_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Parse certificate dictionary into a JSON-serializable format.

        Args:
            cert_dict: Raw certificate dictionary from getpeercert()

        Returns:
            Parsed certificate data with dates as ISO strings
        """
        parsed: dict[str, Any] = {}

        # Subject information
        if "subject" in cert_dict:
            subject = {}
            for entry in cert_dict["subject"]:
                for key, value in entry:
                    # Convert to lowercase for consistency
                    subject[key.lower()] = value
            parsed["subject"] = subject

        # Issuer information
        if "issuer" in cert_dict:
            issuer = {}
            for entry in cert_dict["issuer"]:
                for key, value in entry:
                    issuer[key.lower()] = value
            parsed["issuer"] = issuer

        # Version
        if "version" in cert_dict:
            parsed["version"] = cert_dict["version"]

        # Serial number
        if "serialNumber" in cert_dict:
            parsed["serial_number"] = cert_dict["serialNumber"]

        # Validity dates
        if "notBefore" in cert_dict:
            try:
                # Parse date string like 'Jan  1 00:00:00 2023 GMT'
                not_before = datetime.strptime(
                    cert_dict["notBefore"], "%b %d %H:%M:%S %Y %Z"
                )
                parsed["not_before"] = not_before.isoformat()
            except (ValueError, TypeError):
                parsed["not_before"] = cert_dict["notBefore"]

        if "notAfter" in cert_dict:
            try:
                not_after = datetime.strptime(
                    cert_dict["notAfter"], "%b %d %H:%M:%S %Y %Z"
                )
                parsed["not_after"] = not_after.isoformat()
            except (ValueError, TypeError):
                parsed["not_after"] = cert_dict["notAfter"]

        # Subject Alternative Names (SANs)
        if "subjectAltName" in cert_dict:
            sans = []
            for san_type, san_value in cert_dict["subjectAltName"]:
                sans.append({"type": san_type, "value": san_value})
            parsed["subject_alt_names"] = sans

        # OCSP and CA Issuers
        if "OCSP" in cert_dict:
            parsed["ocsp"] = cert_dict["OCSP"]

        if "caIssuers" in cert_dict:
            parsed["ca_issuers"] = cert_dict["caIssuers"]

        # Certificate revocation lists
        if "crlDistributionPoints" in cert_dict:
            parsed["crl_distribution_points"] = cert_dict["crlDistributionPoints"]

        return parsed
