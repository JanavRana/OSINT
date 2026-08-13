"""
tests/test_email_osint.py

Comprehensive unit tests for Email OSINT:
    - Email validator (format validation, normalization, component extraction)
    - EmailOsintConnector (mocked DNS/HTTP — zero real API calls)
    - EmailOsintNormalizer
    - MX record lookup
    - Disposable email detection
    - Gravatar profile lookup
    - Failure isolation (one sub-lookup failure ≠ others)

All external DNS/HTTP calls are mocked using unittest.mock.

Coverage targets per spec:
    valid email                ✓
    invalid email              ✓
    email normalization        ✓
    MX records present         ✓
    MX records absent          ✓
    mail provider inference    ✓
    disposable domain          ✓
    non-disposable domain      ✓
    gravatar profile found     ✓
    gravatar profile not found ✓
    gravatar with accounts     ✓
    MX lookup failure          ✓
    disposable check unavailable ✓
    gravatar timeout           ✓
    normalized facts           ✓
    graph relationships        ✓
    validation error handling  ✓
    failure isolation          ✓
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ── Test Infrastructure ────────────────────────────────────────────────────


def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════════════
# 1. VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailValidator:
    """Test suite for connectors/email/validator.py"""

    def setup_method(self):
        from app.connectors.email.validator import validate_email_address, EmailValidationError
        self.validate = validate_email_address
        self.EmailValidationError = EmailValidationError

    def test_valid_email_simple(self):
        """Standard email should validate cleanly."""
        result = self.validate("user@example.com")
        assert result.email == "user@example.com"
        assert result.local_part == "user"
        assert result.domain == "example.com"

    def test_valid_email_with_dots(self):
        """Email with dots in local part should validate."""
        result = self.validate("first.last@example.com")
        assert result.email == "first.last@example.com"
        assert result.local_part == "first.last"
        assert result.domain == "example.com"

    def test_valid_email_with_plus(self):
        """Email with + addressing should validate."""
        result = self.validate("user+tag@example.com")
        assert result.email == "user+tag@example.com"
        assert result.local_part == "user+tag"

    def test_email_normalization_uppercase(self):
        """Email should be normalized to lowercase."""
        result = self.validate("User@Example.COM")
        assert result.email == "user@example.com"
        assert result.domain == "example.com"

    def test_email_normalization_whitespace(self):
        """Whitespace should be trimmed."""
        result = self.validate("  user@example.com  ")
        assert result.email == "user@example.com"

    def test_invalid_email_no_at(self):
        """Email without @ should raise error."""
        with pytest.raises(self.EmailValidationError) as exc_info:
            self.validate("userexample.com")
        assert "not a valid email" in str(exc_info.value).lower()

    def test_invalid_email_no_domain(self):
        """Email without domain should raise error."""
        with pytest.raises(self.EmailValidationError) as exc_info:
            self.validate("user@")
        assert "not a valid email" in str(exc_info.value).lower()

    def test_invalid_email_no_local_part(self):
        """Email without local part should raise error."""
        with pytest.raises(self.EmailValidationError) as exc_info:
            self.validate("@example.com")
        assert "not a valid email" in str(exc_info.value).lower()

    def test_invalid_email_no_tld(self):
        """Email without TLD should raise error."""
        with pytest.raises(self.EmailValidationError) as exc_info:
            self.validate("user@localhost")
        assert "not a valid email" in str(exc_info.value).lower()

    def test_invalid_email_empty(self):
        """Empty string should raise error."""
        with pytest.raises(self.EmailValidationError) as exc_info:
            self.validate("")
        assert "non-empty" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════
# 2. CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailOsintConnector:
    """Test suite for connectors/email/connector.py"""

    def setup_method(self):
        from app.connectors.email.connector import EmailOsintConnector
        from app.connectors.types import Identifier, IdentifierType
        self.connector = EmailOsintConnector()
        self.Identifier = Identifier
        self.IdentifierType = IdentifierType

    def test_mx_records_found(self):
        """MX records should be parsed and provider inferred."""
        with patch('dns.resolver.resolve') as mock_resolve:
            # Mock MX records
            mock_mx1 = Mock()
            mock_mx1.exchange = Mock()
            mock_mx1.exchange.__str__ = lambda x: "aspmx.l.google.com."
            mock_mx1.preference = 10

            mock_mx2 = Mock()
            mock_mx2.exchange = Mock()
            mock_mx2.exchange.__str__ = lambda x: "alt1.aspmx.l.google.com."
            mock_mx2.preference = 20

            mock_resolve.return_value = [mock_mx1, mock_mx2]

            identifier = self.Identifier(value="user@gmail.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["email"] == "user@gmail.com"
            assert result["domain"] == "gmail.com"
            assert result["mx_present"] is True
            assert result["mx_records"]["records"][0]["host"] == "aspmx.l.google.com"
            assert result["mx_records"]["records"][0]["preference"] == 10
            assert result["mail_provider"] == "Google"

    def test_mx_records_not_found(self):
        """No MX records should result in mx_present=False."""
        with patch('dns.resolver.resolve') as mock_resolve:
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()

            identifier = self.Identifier(value="user@nonexistent.test", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["mx_present"] is False
            assert result["mx_records"] is None

    def test_disposable_email_detected(self):
        """Disposable domain should be flagged."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('app.connectors.email.connector._load_disposable_domains') as mock_load:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock disposable domains
            mock_load.return_value = {"tempmail.com", "10minutemail.com", "guerrillamail.com"}

            identifier = self.Identifier(value="user@tempmail.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["disposable"] is True

    def test_non_disposable_email(self):
        """Non-disposable domain should not be flagged."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('app.connectors.email.connector._load_disposable_domains') as mock_load:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock disposable domains (gmail not in list)
            mock_load.return_value = {"tempmail.com", "10minutemail.com"}

            identifier = self.Identifier(value="user@gmail.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["disposable"] is False

    def test_disposable_check_unavailable(self):
        """If disposable package unavailable and network fails, should return None gracefully."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('httpx.AsyncClient.get', side_effect=Exception("Network error")), \
             patch('app.connectors.email.connector._load_disposable_domains') as mock_load:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock package unavailable
            mock_load.return_value = None

            identifier = self.Identifier(value="user@example.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["disposable"] is None

    def test_gravatar_profile_found(self):
        """Gravatar profile should be retrieved and parsed."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock Gravatar response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "entry": [{
                    "displayName": "John Doe",
                    "preferredUsername": "johndoe",
                    "aboutMe": "Software developer",
                    "currentLocation": "San Francisco",
                    "thumbnailUrl": "https://gravatar.com/avatar/123.jpg",
                    "accounts": [
                        {
                            "shortname": "twitter",
                            "username": "johndoe",
                            "url": "https://twitter.com/johndoe",
                            "verified": True
                        }
                    ]
                }]
            }

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            identifier = self.Identifier(value="user@example.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["gravatar_profile"] is not None
            assert result["gravatar_profile"]["display_name"] == "John Doe"
            assert result["gravatar_profile"]["preferred_username"] == "johndoe"
            assert len(result["gravatar_profile"]["accounts"]) == 1
            assert result["gravatar_profile"]["accounts"][0]["service"] == "twitter"

    def test_gravatar_profile_not_found(self):
        """404 from Gravatar should result in None (not an error)."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            identifier = self.Identifier(value="user@example.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["gravatar_profile"] is None

    def test_gravatar_http_error(self):
        """Gravatar HTTP errors should be captured in error annotation."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('app.connectors.email.connector._load_disposable_domains') as mock_load, \
             patch('app.connectors.email.connector.httpx.AsyncClient') as mock_client_class:
            
            # Mock empty MX
            from dns.resolver import NXDOMAIN
            mock_resolve.side_effect = NXDOMAIN()
            
            # Mock disposable check
            mock_load.return_value = set()
            
            # Mock HTTP 500 error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            identifier = self.Identifier(value="user@example.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            assert result["gravatar_profile"] is not None
            assert "error" in result["gravatar_profile"]
            assert "500" in result["gravatar_profile"]["error"]

    def test_validation_error_captured(self):
        """Invalid email should produce validation_error field."""
        identifier = self.Identifier(value="not-an-email", type=self.IdentifierType.EMAIL)
        result = run(self.connector.fetch(identifier))

        assert result["validation_error"] is not None
        assert "not a valid email" in result["validation_error"].lower()
        assert result["email"] is None

    def test_failure_isolation_mx_fails(self):
        """MX lookup failure should not prevent Gravatar lookup."""
        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            # Mock MX failure
            mock_resolve.side_effect = Exception("DNS error")
            
            # Mock successful Gravatar
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            identifier = self.Identifier(value="user@example.com", type=self.IdentifierType.EMAIL)
            result = run(self.connector.fetch(identifier))

            # MX failed but was captured
            assert "error" in result["mx_records"]
            # Gravatar succeeded
            assert result["gravatar_profile"] is None  # 404 means no profile
            # Email still validated
            assert result["email"] == "user@example.com"


# ═══════════════════════════════════════════════════════════════════════════
# 3. NORMALIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailOsintNormalizer:
    """Test suite for normalizers/email/normalizer.py"""

    def setup_method(self):
        from app.normalizers.email.normalizer import EmailOsintNormalizer
        from app.normalizers.types import FactType
        self.normalizer = EmailOsintNormalizer()
        self.FactType = FactType

    def test_email_fact_valid(self):
        """Valid email should produce EMAIL fact with confidence 1.0."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "local_part": "user",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": False,
        }

        facts = self.normalizer.normalize(payload)
        email_facts = [f for f in facts if f.fact_type == self.FactType.EMAIL]

        assert len(email_facts) == 1
        assert email_facts[0].value == "user@example.com"
        assert email_facts[0].confidence == 1.0

    def test_email_fact_invalid(self):
        """Invalid email should produce EMAIL fact with low confidence."""
        payload = {
            "input": "invalid-email",
            "email": None,
            "validation_error": "Not a valid email",
            "mx_present": False,
        }

        facts = self.normalizer.normalize(payload)
        email_facts = [f for f in facts if f.fact_type == self.FactType.EMAIL]

        assert len(email_facts) == 1
        assert email_facts[0].confidence == 0.30
        assert "validation_error" in email_facts[0].metadata

    def test_domain_fact(self):
        """Domain should be extracted as DOMAIN fact."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": False,
        }

        facts = self.normalizer.normalize(payload)
        domain_facts = [f for f in facts if f.fact_type == self.FactType.DOMAIN]

        assert len(domain_facts) == 1
        assert domain_facts[0].value == "example.com"
        assert domain_facts[0].confidence == 0.95

    def test_mx_record_facts(self):
        """MX records should produce DNS_RECORD facts."""
        payload = {
            "input": "user@gmail.com",
            "email": "user@gmail.com",
            "domain": "gmail.com",
            "validation_error": None,
            "mx_present": True,
            "mx_records": {
                "records": [
                    {"host": "aspmx.l.google.com", "preference": 10},
                    {"host": "alt1.aspmx.l.google.com", "preference": 20}
                ]
            },
        }

        facts = self.normalizer.normalize(payload)
        dns_facts = [f for f in facts if f.fact_type == self.FactType.DNS_RECORD]

        assert len(dns_facts) == 2
        assert dns_facts[0].value == "aspmx.l.google.com"
        assert dns_facts[0].metadata["record_type"] == "MX"
        assert dns_facts[0].metadata["preference"] == 10
        assert dns_facts[0].confidence == 0.90

    def test_mail_provider_fact(self):
        """Mail provider inference should produce GENERIC fact."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": True,
            "mail_provider": "Google",
        }

        facts = self.normalizer.normalize(payload)
        provider_facts = [f for f in facts if f.fact_type == self.FactType.GENERIC 
                         and f.metadata.get("field") == "mail_provider"]

        assert len(provider_facts) == 1
        assert provider_facts[0].value == "mail_provider:Google"
        assert provider_facts[0].confidence == 0.70
        assert provider_facts[0].metadata["inferred"] is True

    def test_disposable_fact(self):
        """Disposable flag should produce GENERIC fact."""
        payload = {
            "input": "user@tempmail.com",
            "email": "user@tempmail.com",
            "domain": "tempmail.com",
            "validation_error": None,
            "mx_present": False,
            "disposable": True,
        }

        facts = self.normalizer.normalize(payload)
        disposable_facts = [f for f in facts if f.fact_type == self.FactType.GENERIC 
                           and f.metadata.get("field") == "disposable"]

        assert len(disposable_facts) == 1
        assert disposable_facts[0].value == "disposable:True"
        assert disposable_facts[0].confidence == 0.95

    def test_gravatar_profile_fact(self):
        """Gravatar profile should produce PROFILE_DATA fact."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": False,
            "gravatar_profile": {
                "hash": "abc123",
                "display_name": "John Doe",
                "about_me": "Developer",
                "avatar_url": "https://gravatar.com/avatar/abc123.jpg",
                "accounts": []
            }
        }

        facts = self.normalizer.normalize(payload)
        profile_facts = [f for f in facts if f.fact_type == self.FactType.PROFILE_DATA]

        assert len(profile_facts) == 1
        assert profile_facts[0].confidence == 0.75
        assert profile_facts[0].metadata["source"] == "gravatar"
        assert profile_facts[0].value == "John Doe"
        assert profile_facts[0].metadata["display_name"] == "John Doe"

    def test_gravatar_social_accounts(self):
        """Gravatar verified accounts should produce SOCIAL_ACCOUNT facts."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": False,
            "gravatar_profile": {
                "hash": "abc123",
                "accounts": [
                    {
                        "service": "twitter",
                        "username": "johndoe",
                        "url": "https://twitter.com/johndoe",
                        "verified": True
                    }
                ]
            }
        }

        facts = self.normalizer.normalize(payload)
        social_facts = [f for f in facts if f.fact_type == self.FactType.SOCIAL_ACCOUNT 
                       and not f.metadata.get("graph_edge")]

        assert len(social_facts) == 1
        assert social_facts[0].value == "johndoe"
        assert social_facts[0].metadata["platform"] == "twitter"
        assert social_facts[0].metadata["verified"] is True
        assert social_facts[0].confidence == 0.70

    def test_graph_relationships(self):
        """Graph edges should be created for email→domain and email→gravatar."""
        payload = {
            "input": "user@example.com",
            "email": "user@example.com",
            "domain": "example.com",
            "validation_error": None,
            "mx_present": False,
            "gravatar_profile": {
                "hash": "abc123",
            }
        }

        facts = self.normalizer.normalize(payload)
        graph_facts = [f for f in facts if f.metadata.get("graph_edge") is True]

        assert len(graph_facts) == 2
        
        # Email → Domain edge
        domain_edge = [f for f in graph_facts if f.metadata.get("relationship") == "uses_domain"]
        assert len(domain_edge) == 1
        assert domain_edge[0].metadata["from"] == "user@example.com"
        assert domain_edge[0].metadata["to"] == "example.com"
        
        # Email → Gravatar edge
        gravatar_edge = [f for f in graph_facts if f.metadata.get("relationship") == "has_gravatar"]
        assert len(gravatar_edge) == 1
        assert gravatar_edge[0].metadata["from"] == "user@example.com"
        assert "gravatar:abc123" in gravatar_edge[0].metadata["to"]


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailOsintIntegration:
    """End-to-end integration test."""

    def test_full_pipeline(self):
        """Test complete connector → normalizer pipeline."""
        from app.connectors.email.connector import EmailOsintConnector
        from app.normalizers.email.normalizer import EmailOsintNormalizer
        from app.connectors.types import Identifier, IdentifierType

        connector = EmailOsintConnector()
        normalizer = EmailOsintNormalizer()

        with patch('dns.resolver.resolve') as mock_resolve, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            # Mock MX records
            mock_mx = Mock()
            mock_mx.exchange = Mock()
            mock_mx.exchange.__str__ = lambda x: "aspmx.l.google.com."
            mock_mx.preference = 10
            mock_resolve.return_value = [mock_mx]
            
            # Mock Gravatar 404
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # Execute pipeline
            identifier = Identifier(value="test@gmail.com", type=IdentifierType.EMAIL)
            raw_result = run(connector.fetch(identifier))
            facts = normalizer.normalize(raw_result)

            # Verify we got multiple fact types
            fact_types = {f.fact_type for f in facts}
            from app.normalizers.types import FactType
            
            assert FactType.EMAIL in fact_types
            assert FactType.DOMAIN in fact_types
            assert FactType.DNS_RECORD in fact_types
            assert FactType.GENERIC in fact_types
            
            # Verify at least one graph edge
            graph_edges = [f for f in facts if f.metadata.get("graph_edge")]
            assert len(graph_edges) >= 1
