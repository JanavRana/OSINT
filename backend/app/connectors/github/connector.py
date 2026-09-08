"""
connectors/github/connector.py

GitHub REST API Bi-Directional OSINT Connector.

Queries GitHub REST API v3 for USERNAME and EMAIL identifiers to extract:
- Bi-directional identity mapping (Username ↔ Email)
- Public email address & commit-history disclosed emails
- Full name, bio, company/employer, location
- Twitter handle, blog/portfolio website, public repos & followers count
- Account creation timestamp & avatar photo URL
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar, Dict, FrozenSet, List, Set

import httpx

from ...core.config import get_settings
from ..base import BaseConnector
from ..registry import registry
from ..types import Identifier, IdentifierType

logger = logging.getLogger("osint-aggregator")


@registry.register
class GitHubConnector(BaseConnector):
    """
    GitHub REST API Bi-Directional OSINT Connector.

    Supports `IdentifierType.USERNAME` and `IdentifierType.EMAIL`.
    Queries GitHub REST API v3 using optional token authentication for high rate limits (5,000 req/hr).
    """

    name: ClassVar[str] = "github"
    supported_identifier_types: ClassVar[FrozenSet[IdentifierType]] = frozenset(
        {IdentifierType.USERNAME, IdentifierType.EMAIL}
    )
    timeout_seconds: ClassVar[float] = 10.0

    async def fetch(self, identifier: Identifier) -> Dict[str, Any]:
        """
        Query GitHub REST API for username or email address.
        """
        raw_value = identifier.value.strip()
        settings = get_settings()

        result: Dict[str, Any] = {
            "query_target": raw_value,
            "target_type": identifier.type.value,
            "github_matched": False,
            "username": None,
            "display_name": None,
            "email": None,
            "discovered_emails": [],
            "bio": None,
            "company": None,
            "location": None,
            "blog": None,
            "twitter_username": None,
            "public_repos": None,
            "followers": None,
            "following": None,
            "created_at": None,
            "avatar_url": None,
            "profile_url": None,
            "error": None,
            "error_code": None,
        }

        # Retrieve GITHUB_TOKEN if available
        token = (
            os.environ.get("GITHUB_TOKEN")
            or getattr(settings, "github_token", None)
        )
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OSINT-Aggregator/1.0",
        }
        if token and token.strip():
            tok_val = token.strip()
            headers["Authorization"] = f"Bearer {tok_val}" if not tok_val.startswith("Bearer ") else tok_val

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            if identifier.type == IdentifierType.USERNAME:
                await self._fetch_by_username(client, raw_value, headers, result)
            elif identifier.type == IdentifierType.EMAIL:
                await self._fetch_by_email(client, raw_value, headers, result)
            else:
                result["error"] = f"Unsupported identifier type: {identifier.type}"
                result["error_code"] = "unsupported_type"

        return result

    async def _fetch_by_username(
        self, client: httpx.AsyncClient, username: str, headers: Dict[str, str], result: Dict[str, Any]
    ) -> None:
        """
        Fetch profile data and public commit activity emails for a given GitHub username.
        """
        url = f"https://api.github.com/users/{username}"
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                self._populate_user_fields(data, result)
                result["github_matched"] = True

                # Secondary lookup: Check public events for hidden commit author emails
                await self._fetch_commit_emails(client, username, headers, result)

            elif resp.status_code == 404:
                logger.info("GitHub user %s not found.", username)
                result["error"] = "GitHub user not found"
                result["error_code"] = 404
            elif resp.status_code in (401, 403):
                logger.warning("GitHub API rate limit or auth error (HTTP %s) for %s", resp.status_code, username)
                result["error"] = "Rate limit exceeded or invalid token"
                result["error_code"] = resp.status_code
            else:
                logger.warning("GitHub API HTTP %s for user %s", resp.status_code, username)
                result["error"] = f"HTTP {resp.status_code}"
                result["error_code"] = resp.status_code
        except Exception as exc:
            logger.warning("GitHub API request error for user %s: %s", username, exc)
            result["error"] = str(exc)
            result["error_code"] = "provider_error"

    async def _fetch_by_email(
        self, client: httpx.AsyncClient, email: str, headers: Dict[str, str], result: Dict[str, Any]
    ) -> None:
        """
        Search GitHub for users matching a target email address (Email -> Username pivot).
        Only queries GitHub for emails belonging to github domains (@github.com or @users.noreply.github.com).
        """
        clean_email = email.lower().strip()
        if not (clean_email.endswith("@github.com") or clean_email.endswith("@users.noreply.github.com")):
            logger.info("Skipping GitHub lookup for non-GitHub domain email: %s", email)
            result["error"] = "Skipping GitHub lookup for non-GitHub email domain"
            result["error_code"] = "non_github_domain"
            return

        url = f"https://api.github.com/search/users?q={email}+in:email"

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items") or []
                if items and isinstance(items, list):
                    top_match = items[0]
                    matched_username = top_match.get("login")
                    if matched_username:
                        # Perform full profile lookup for the matched username
                        await self._fetch_by_username(client, matched_username, headers, result)
                        result["email"] = email
                else:
                    logger.info("No GitHub user found matching email %s", email)
                    result["error"] = "No GitHub user matching email"
                    result["error_code"] = 404
            elif resp.status_code in (401, 403):
                result["error"] = "Rate limit exceeded or auth error"
                result["error_code"] = resp.status_code
            else:
                result["error"] = f"HTTP {resp.status_code}"
                result["error_code"] = resp.status_code
        except Exception as exc:
            logger.warning("GitHub email search error for %s: %s", email, exc)
            result["error"] = str(exc)
            result["error_code"] = "provider_error"

    async def _fetch_commit_emails(
        self, client: httpx.AsyncClient, username: str, headers: Dict[str, str], result: Dict[str, Any]
    ) -> None:
        """
        Scan public events log to extract raw commit author email disclosures.
        """
        events_url = f"https://api.github.com/users/{username}/events/public"
        try:
            resp = await client.get(events_url, headers=headers)
            if resp.status_code == 200:
                events = resp.json()
                discovered: Set[str] = set()

                if isinstance(events, list):
                    for evt in events[:15]:  # Inspect recent 15 events
                        payload = evt.get("payload") or {}
                        commits = payload.get("commits") or []
                        if isinstance(commits, list):
                            for commit in commits:
                                author = commit.get("author") or {}
                                email_val = author.get("email")
                                if (
                                    email_val
                                    and isinstance(email_val, str)
                                    and "@" in email_val
                                    and not email_val.endswith("@users.noreply.github.com")
                                ):
                                    discovered.add(email_val.strip().lower())

                if discovered:
                    result["discovered_emails"] = list(discovered)
                    if not result.get("email"):
                        result["email"] = list(discovered)[0]
        except Exception as exc:
            logger.debug("Failed to fetch GitHub public events for %s: %s", username, exc)

    def _populate_user_fields(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Helper to extract standard profile fields from GitHub user dict."""
        result["username"] = data.get("login")
        result["display_name"] = data.get("name")
        result["email"] = data.get("email") or result.get("email")
        result["bio"] = data.get("bio")
        result["company"] = data.get("company")
        result["location"] = data.get("location")
        result["blog"] = data.get("blog")
        result["twitter_username"] = data.get("twitter_username")
        result["public_repos"] = data.get("public_repos")
        result["followers"] = data.get("followers")
        result["following"] = data.get("following")
        result["created_at"] = data.get("created_at")
        result["avatar_url"] = data.get("avatar_url")
        result["profile_url"] = data.get("html_url") or f"https://github.com/{data.get('login')}"
