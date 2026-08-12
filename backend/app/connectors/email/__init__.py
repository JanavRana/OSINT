"""
connectors/email/

Email OSINT connector package.

Provides email address validation and OSINT lookups including:
- MX record resolution
- Disposable email detection
- Gravatar public profile lookup
"""

from .connector import EmailOsintConnector
from .validator import EmailValidationError, validate_email_address

__all__ = [
    "EmailOsintConnector",
    "EmailValidationError",
    "validate_email_address",
]
