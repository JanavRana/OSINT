"""
normalizers/github/normalizer.py

GitHub Normalizer.

Transforms raw GitHub REST API payload into normalized facts:
- Username & Profile link
- Public email address & commit-history disclosed emails
- Display name, bio, account creation timestamp, avatar photo URL
- Company / employer & Location
- Twitter handle & personal blog URL
- Repository & follower counts
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact

logger = logging.getLogger("osint-aggregator")


@normalizer_registry.register
class GitHubNormalizer(BaseNormalizer):
    """
    Normalizer for GitHub REST API raw payload.
    """

    connector_name: ClassVar[str] = "github"

    def normalize(self, raw_data: Any) -> List[NormalizedFact]:
        """
        Transform raw GitHub dict payload into normalized facts.
        """
        if not isinstance(raw_data, dict):
            raise NormalizationError(
                f"GitHubNormalizer expected dict, got {type(raw_data).__name__}"
            )

        facts: List[NormalizedFact] = []

        if not raw_data.get("github_matched"):
            return facts

        # Extract Email Address (Primary Profile Email or Discovered Commit Emails)
        email = raw_data.get("email")
        if email and isinstance(email, str) and "@" in email:
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.EMAIL,
                    value=email.strip().lower(),
                    confidence=0.95,
                    metadata={
                        "field": "github_email",
                        "email": email.strip().lower(),
                        "source": "GitHub Profile Email",
                    },
                )
            )

        disc_emails = raw_data.get("discovered_emails") or []
        if isinstance(disc_emails, list):
            for disc_e in disc_emails:
                if disc_e and isinstance(disc_e, str) and disc_e.strip().lower() != (email.strip().lower() if email else ""):
                    facts.append(
                        NormalizedFact(
                            source_connector=self.connector_name,
                            fact_type=FactType.EMAIL,
                            value=disc_e.strip().lower(),
                            confidence=0.90,
                            metadata={
                                "field": "github_commit_email",
                                "email": disc_e.strip().lower(),
                                "source": "GitHub Public Commit History",
                            },
                        )
                    )

        return facts

