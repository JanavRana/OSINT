"""
connectors/email/connector.py

Email OSINT connector using public/technical data sources.

This connector:
    1. Subclasses BaseConnector and registers via @registry.register.
    2. Accepts only EMAIL identifiers.
    3. Performs three concurrent sub-lookups:
       - MX record lookup (dnspython)
       - Disposable email domain detection (disposable-email-domains)
       - Gravatar public profile lookup (httpx + SHA-256)
    4. Returns a raw JSON-serializable dictionary for downstream
       normalization (M3). It performs NO normalization itself.
    5. Isolates failures — one sub-lookup failure does NOT prevent others.

IMPORTANT — Responsible-use boundary:
    This connector accesses only public, technical data:
    - DNS MX records (public infrastructure)
    - Disposable domain list (offline static data)
    - Gravatar profiles (user-published, public profiles only)
    
    It does NOT perform:
    - Email breach database lookups
    - Mailbox verification / SMTP probing
    - Private account enumeration
    - Platform-specific email discovery
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, ClassVar, Dict, FrozenSet, Optional

import dns.resolver
import httpx

from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType
from .validator import EmailValidationError, validate_email_address

# Lazy-load disposable email domains to handle import failures gracefully
_DISPOSABLE_DOMAINS: Optional[set] = None


def _load_disposable_domains() -> Optional[set]:
    """
    Lazy-load the disposable email domains set.
    Returns None if the package is not available (graceful degradation).
    """
    global _DISPOSABLE_DOMAINS
    if _DISPOSABLE_DOMAINS is not None:
        return _DISPOSABLE_DOMAINS
    
    try:
        from disposable_email_domains import blocklist
        _DISPOSABLE_DOMAINS = set(blocklist)
        return _DISPOSABLE_DOMAINS
    except ImportError:
        # Package not installed — graceful fallback
        _DISPOSABLE_DOMAINS = None
        return None


@registry.register
class EmailOsintConnector(BaseConnector):
    """
    Email OSINT connector — performs public/technical lookups on email addresses.

    Produces a structured dict containing:
        - Normalized email address and extracted components (local_part, domain)
        - MX records for the domain (if resolvable)
        - Mail provider inference (based on MX hostnames)
        - Disposable email detection (offline check)
        - Gravatar public profile data (if profile exists)
        - Error annotations for any failed sub-lookup (isolated, non-blocking)

    All sub-lookups run concurrently via asyncio.gather with return_exceptions=True,
    so failure of one does NOT prevent the others from completing.
    """

    name: ClassVar[str] = "email_osint"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.EMAIL}
    )
    timeout_seconds: ClassVar[float] = 20.0  # Allow time for concurrent lookups

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Perform OSINT lookups on an email address.

        Args:
            identifier: An EMAIL identifier whose value is an email address string.

        Returns:
            A JSON-serializable dict with all extracted facts and error annotations.
            The envelope is always returned (never raises) — individual sub-lookup
            failures are captured in the result dict.
        """
        raw_value = identifier.value.strip()
        result: Dict[str, Any] = {
            "input": raw_value,
            "email": None,
            "local_part": None,
            "domain": None,
            "validation_error": None,
            "mx_records": None,
            "mx_present": None,
            "mail_provider": None,
            "disposable": None,
            "gravatar_profile": None,
        }

        # ── Validate ───────────────────────────────────────────────────────
        try:
            validation = validate_email_address(raw_value)
            result["email"] = validation.email
            result["local_part"] = validation.local_part
            result["domain"] = validation.domain
        except EmailValidationError as exc:
            result["validation_error"] = str(exc)
            return result

        # ── Run sub-lookups concurrently ───────────────────────────────────
        # Each sub-lookup is isolated — exceptions are caught and returned
        domain = validation.domain
        email = validation.email

        tasks = [
            self._lookup_mx(domain),
            self._check_disposable(domain),
            self._lookup_gravatar(email),
        ]

        mx_result, disposable_result, gravatar_result = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        # ── Process MX lookup result ───────────────────────────────────────
        if isinstance(mx_result, Exception):
            result["mx_records"] = {"error": str(mx_result)}
            result["mx_present"] = False
        elif mx_result:
            result["mx_records"] = mx_result
            result["mx_present"] = len(mx_result.get("records", [])) > 0
            result["mail_provider"] = mx_result.get("provider")
        else:
            result["mx_present"] = False

        # ── Process disposable check result ────────────────────────────────
        if isinstance(disposable_result, Exception):
            result["disposable"] = {"error": str(disposable_result)}
        else:
            result["disposable"] = disposable_result

        # ── Process Gravatar lookup result ─────────────────────────────────
        if isinstance(gravatar_result, Exception):
            result["gravatar_profile"] = {"error": str(gravatar_result)}
        else:
            result["gravatar_profile"] = gravatar_result

        return result

    async def _lookup_mx(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Perform MX record lookup for the email domain using dnspython.

        Args:
            domain: The email domain to query

        Returns:
            Dict with 'records' (list of MX hosts with preference) and optional 'provider'
            inference, or None if no MX records found
        """
        try:
            # dnspython is sync, wrap in thread executor for async
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(
                None, dns.resolver.resolve, domain, 'MX'
            )

            records = []
            mx_hosts = []
            for rdata in answers:
                mx_host = str(rdata.exchange).rstrip('.')
                records.append({
                    "host": mx_host,
                    "preference": rdata.preference,
                })
                mx_hosts.append(mx_host.lower())

            # Sort by preference (lower is higher priority)
            records.sort(key=lambda x: x["preference"])

            # Infer mail provider from MX hostnames
            provider = self._infer_mail_provider(mx_hosts)

            return {
                "records": records,
                "provider": provider,
            }

        except dns.resolver.NXDOMAIN:
            # Domain doesn't exist
            return None
        except dns.resolver.NoAnswer:
            # Domain exists but no MX records
            return None
        except dns.resolver.NoNameservers:
            # All nameservers failed
            return None
        except Exception as exc:
            # Propagate as exception to be caught by gather()
            raise Exception(f"MX lookup failed: {exc}") from exc

    def _infer_mail_provider(self, mx_hosts: list[str]) -> Optional[str]:
        """
        Infer the mail provider from MX hostnames.

        This is heuristic-based pattern matching, NOT authoritative.
        Confidence should be reduced in the normalizer.
        """
        if not mx_hosts:
            return None

        mx_str = ' '.join(mx_hosts)

        # Common provider patterns
        if 'google.com' in mx_str or 'googlemail.com' in mx_str:
            return "Google"
        elif 'outlook.com' in mx_str or 'microsoft.com' in mx_str:
            return "Microsoft"
        elif 'yahoodns.net' in mx_str or 'yahoo.com' in mx_str:
            return "Yahoo"
        elif 'proofpoint.com' in mx_str:
            return "Proofpoint"
        elif 'mimecast.com' in mx_str:
            return "Mimecast"
        elif 'messagelabs.com' in mx_str:
            return "Symantec"
        elif 'pphosted.com' in mx_str:
            return "Proofpoint"
        elif 'mailgun.org' in mx_str:
            return "Mailgun"
        elif 'sendgrid.net' in mx_str:
            return "SendGrid"
        
        return None

    async def _check_disposable(self, domain: str) -> Optional[bool]:
        """
        Check if the domain is a known disposable email provider.

        Uses the disposable-email-domains package (offline static list).
        Returns None if the package is unavailable.

        Args:
            domain: The email domain to check

        Returns:
            True if disposable, False if not, None if check unavailable
        """
        blocklist = _load_disposable_domains()
        if blocklist is None:
            # Package not available — graceful degradation
            return None

        # Check domain and any parent domains
        # e.g., "mail.tempmail.com" should match if "tempmail.com" is blocked
        parts = domain.split('.')
        for i in range(len(parts)):
            check_domain = '.'.join(parts[i:])
            if check_domain in blocklist:
                return True

        return False

    async def _lookup_gravatar(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Look up Gravatar public profile for the email address.

        Gravatar profiles are user-published, public data. This does NOT
        access any private information.

        Args:
            email: The normalized email address

        Returns:
            Dict with profile data if found, None if no profile, or error annotation
        """
        # Try SHA-256 first (Gravatar modern standard), then fallback to MD5 (legacy)
        sha256_hash = hashlib.sha256(email.encode()).hexdigest()
        md5_hash = hashlib.md5(email.encode()).hexdigest()

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # Try SHA-256 profile URL
                response = await client.get(f"https://www.gravatar.com/{sha256_hash}.json")
                if response.status_code == 404:
                    # Fallback to MD5 profile URL
                    response = await client.get(f"https://www.gravatar.com/{md5_hash}.json")

                if response.status_code == 404:
                    # No profile found — this is clean, not an error
                    return None

                if response.status_code != 200:
                    # Other error status
                    return {
                        "error": f"HTTP {response.status_code}",
                        "source": "gravatar",
                    }

                # Parse profile data
                data = response.json()
                if not data or not isinstance(data, dict) or 'entry' not in data:
                    return None

                entries = data.get('entry', [])
                if not entries or not isinstance(entries, list):
                    return None

                # Use first entry
                profile = entries[0]

                # Extract relevant fields
                result = {
                    "hash": email_hash,
                    "profile_url": f"https://www.gravatar.com/{email_hash}",
                    "display_name": profile.get('displayName'),
                    "preferred_username": profile.get('preferredUsername'),
                    "about_me": profile.get('aboutMe'),
                    "current_location": profile.get('currentLocation'),
                    "profile_background_url": profile.get('profileBackground', {}).get('url') if isinstance(profile.get('profileBackground'), dict) else None,
                    "avatar_url": profile.get('thumbnailUrl'),
                    "photos": [],
                    "accounts": [],
                }

                # Extract photos
                photos = profile.get('photos', [])
                if isinstance(photos, list):
                    for photo in photos:
                        if isinstance(photo, dict) and 'value' in photo:
                            result["photos"].append({
                                "url": photo.get('value'),
                                "type": photo.get('type'),
                            })

                # Extract verified accounts
                accounts = profile.get('accounts', [])
                if isinstance(accounts, list):
                    for account in accounts:
                        if isinstance(account, dict):
                            result["accounts"].append({
                                "service": account.get('shortname'),
                                "username": account.get('username'),
                                "url": account.get('url'),
                                "verified": account.get('verified', False),
                            })

                return result

        except httpx.TimeoutException:
            return {
                "error": "Request timeout",
                "source": "gravatar",
            }
        except Exception as exc:
            return {
                "error": f"Lookup failed: {exc}",
                "source": "gravatar",
            }
