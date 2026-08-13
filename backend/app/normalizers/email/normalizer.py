"""
normalizers/email/normalizer.py

Email OSINT normalizer — converts the EmailOsintConnector's raw dict into
normalized facts following the shared internal schema (M3, Section 11.3
of MASTER_DESIGN.md).

Confidence assignments (MASTER_DESIGN.md §4.3 / NFR4 — explainability):

    EMAIL (normalized, structurally valid)          → 1.00
    DOMAIN (extracted from email)                   → 0.95
    DNS_RECORD (MX records)                         → 0.90
    GENERIC (mx_present, disposable flags)          → 0.90-0.95
    GENERIC (mail_provider — inferred from MX)      → 0.70
    PROFILE_DATA (Gravatar profile)                 → 0.75
    SOCIAL_ACCOUNT (Gravatar verified accounts)     → 0.70
    social_account (graph edges: email→domain,
                    email→gravatar)                 → 0.95 (with graph_edge: True)

IMPORTANT: Mail provider inference is heuristic-based, NOT authoritative.
Gravatar data is user-published and may be outdated. Confidence scores
reflect these limitations.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class EmailOsintNormalizer(BaseNormalizer):
    """
    Normalizer for the 'email_osint' connector's raw payload.

    Extracts NormalizedFact instances from the structured dict produced
    by EmailOsintConnector.fetch():

        - EMAIL fact:        the normalized email address
        - DOMAIN fact:       extracted domain component
        - DNS_RECORD facts:  MX records for the domain
        - GENERIC facts:     mx_present, mail_provider, disposable flags
        - PROFILE_DATA fact: Gravatar profile (if found)
        - SOCIAL_ACCOUNT facts: Gravatar verified accounts (if any)
        - Graph edges:       email→domain, email→gravatar relationships

    If validation failed, a low-confidence EMAIL fact is still produced
    for audit trail purposes.
    """

    connector_name: ClassVar[str] = "email_osint"

    # ── Confidence constants ───────────────────────────────────────────────
    _CONF_EMAIL_VALID: float = 1.00          # structurally valid email
    _CONF_EMAIL_INVALID: float = 0.30        # validation failed
    _CONF_DOMAIN: float = 0.95               # domain extracted from email
    _CONF_MX_RECORD: float = 0.90            # DNS MX record
    _CONF_MX_PRESENT: float = 0.90           # boolean flag: MX exists
    _CONF_DISPOSABLE: float = 0.95           # disposable domain check (offline)
    _CONF_PROVIDER: float = 0.70             # inferred provider (heuristic)
    _CONF_GRAVATAR_PROFILE: float = 0.75     # Gravatar profile data
    _CONF_GRAVATAR_ACCOUNT: float = 0.70     # Gravatar verified accounts
    _CONF_GRAPH_EDGE: float = 0.95           # relationship edges

    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        """
        Convert EmailOsintConnector's raw dict into normalized facts.

        Args:
            raw_payload: The dict returned by EmailOsintConnector.fetch().

        Returns:
            A list of NormalizedFact instances. Always at least one EMAIL
            fact (even on validation failure, for audit trail).

        Raises:
            NormalizationError: If raw_payload is not a dict at all.
        """
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}",
            )

        facts: List[NormalizedFact] = []

        validation_error = raw_payload.get("validation_error")
        email = raw_payload.get("email")
        domain = raw_payload.get("domain")

        # ── 1. Primary EMAIL fact ──────────────────────────────────────────
        email_fact = self._build_email_fact(raw_payload, email, validation_error)
        facts.append(email_fact)

        # Stop here if validation failed
        if validation_error:
            return facts

        # ── 2. DOMAIN fact ─────────────────────────────────────────────────
        if domain:
            domain_fact = self._build_domain_fact(domain)
            facts.append(domain_fact)

        # ── 3. MX records and flags ────────────────────────────────────────
        mx_records = raw_payload.get("mx_records")
        mx_present = raw_payload.get("mx_present", False)
        mail_provider = raw_payload.get("mail_provider")

        if mx_records and isinstance(mx_records, dict) and not mx_records.get("error"):
            mx_facts = self._build_mx_facts(mx_records)
            facts.extend(mx_facts)

        # MX present flag
        mx_present_fact = self._build_generic_fact(
            "mx_present",
            mx_present,
            self._CONF_MX_PRESENT,
            {"field": "mx_present", "description": "Email domain has MX records"}
        )
        facts.append(mx_present_fact)

        # Mail provider inference
        if mail_provider:
            provider_fact = self._build_generic_fact(
                "mail_provider",
                mail_provider,
                self._CONF_PROVIDER,
                {
                    "field": "mail_provider",
                    "inferred": True,
                    "note": "Provider inferred from MX hostnames (heuristic-based)",
                }
            )
            facts.append(provider_fact)

        # ── 4. Disposable email flag ───────────────────────────────────────
        disposable = raw_payload.get("disposable")
        if disposable is not None and not isinstance(disposable, dict):
            disposable_fact = self._build_generic_fact(
                "disposable",
                disposable,
                self._CONF_DISPOSABLE,
                {
                    "field": "disposable",
                    "description": "Email domain is a known disposable/temporary provider",
                    "source": "disposable-email-domains",
                }
            )
            facts.append(disposable_fact)

        # ── 5. Gravatar profile ────────────────────────────────────────────
        gravatar_profile = raw_payload.get("gravatar_profile")
        if gravatar_profile and isinstance(gravatar_profile, dict) and not gravatar_profile.get("error"):
            gravatar_facts = self._build_gravatar_facts(gravatar_profile, email)
            facts.extend(gravatar_facts)

        # ── 6. Abstract Email Reputation & Data Breaches ───────────────────
        abstract_rep = raw_payload.get("abstract_reputation")
        if abstract_rep and isinstance(abstract_rep, dict) and not abstract_rep.get("error"):
            abstract_facts = self._build_abstract_facts(abstract_rep)
            facts.extend(abstract_facts)

        # ── 7. Graph relationships ─────────────────────────────────────────
        if email and domain:
            graph_facts = self._build_graph_relationships(email, domain, gravatar_profile)
            facts.extend(graph_facts)

        return facts

    # ── Private builders ──────────────────────────────────────────────────

    def _build_email_fact(
        self,
        payload: Dict[str, Any],
        email: Optional[str],
        validation_error: Optional[str],
    ) -> NormalizedFact:
        """Build the primary EMAIL fact."""
        raw_input = payload.get("input", "")
        value = email or raw_input

        if validation_error:
            confidence = self._CONF_EMAIL_INVALID
            metadata = {
                "field": "email",
                "validation_error": validation_error,
                "local_part": payload.get("local_part"),
                "domain": payload.get("domain"),
            }
        else:
            confidence = self._CONF_EMAIL_VALID
            metadata = {
                "field": "email",
                "local_part": payload.get("local_part"),
                "domain": payload.get("domain"),
            }

        return NormalizedFact(
            fact_type=FactType.EMAIL,
            value=value,
            source_connector=self.connector_name,
            confidence=confidence,
            metadata=metadata,
        )

    def _build_domain_fact(self, domain: str) -> NormalizedFact:
        """Build a DOMAIN fact from the extracted email domain."""
        return NormalizedFact(
            fact_type=FactType.DOMAIN,
            value=domain,
            source_connector=self.connector_name,
            confidence=self._CONF_DOMAIN,
            metadata={
                "field": "domain",
                "extracted_from": "email",
            },
        )

    def _build_mx_facts(self, mx_data: Dict[str, Any]) -> List[NormalizedFact]:
        """Build DNS_RECORD facts for each MX record."""
        facts = []
        records = mx_data.get("records", [])

        for record in records:
            if not isinstance(record, dict):
                continue

            host = record.get("host")
            preference = record.get("preference")

            if not host:
                continue

            facts.append(
                NormalizedFact(
                    fact_type=FactType.DNS_RECORD,
                    value=host,
                    source_connector=self.connector_name,
                    confidence=self._CONF_MX_RECORD,
                    metadata={
                        "record_type": "MX",
                        "preference": preference,
                        "field": "mx_record",
                    },
                )
            )

        return facts

    def _build_generic_fact(
        self,
        field: str,
        value: Any,
        confidence: float,
        metadata: Dict[str, Any],
    ) -> NormalizedFact:
        """Build a GENERIC fact with the given parameters."""
        # Include field name in value string to prevent deduplication of boolean generic facts
        val_str = f"{field}:{value}"
        return NormalizedFact(
            fact_type=FactType.GENERIC,
            value=val_str,
            source_connector=self.connector_name,
            confidence=confidence,
            metadata=metadata,
        )

    def _build_gravatar_facts(
        self,
        gravatar_data: Dict[str, Any],
        email: str,
    ) -> List[NormalizedFact]:
        """Build PROFILE_DATA and SOCIAL_ACCOUNT facts from Gravatar profile."""
        facts = []

        display_name = gravatar_data.get("display_name")
        pref_user = gravatar_data.get("preferred_username")
        about_me = gravatar_data.get("about_me")
        location = gravatar_data.get("current_location")
        avatar_url = gravatar_data.get("avatar_url")
        profile_url = gravatar_data.get("profile_url")
        email_hash = gravatar_data.get("hash")

        val_str = display_name or pref_user or profile_url or f"gravatar:{email_hash}"

        facts.append(
            NormalizedFact(
                fact_type=FactType.PROFILE_DATA,
                value=str(val_str),
                source_connector=self.connector_name,
                confidence=self._CONF_GRAVATAR_PROFILE,
                metadata={
                    "field": "gravatar_profile",
                    "source": "gravatar",
                    "display_name": display_name,
                    "preferred_username": pref_user,
                    "about_me": about_me,
                    "current_location": location,
                    "avatar_url": avatar_url,
                    "profile_url": profile_url,
                    "email_hash": email_hash,
                },
            )
        )

        # Verified accounts
        accounts = gravatar_data.get("accounts", [])
        for account in accounts:
            if not isinstance(account, dict):
                continue

            service = account.get("shortname") or account.get("service")
            username = account.get("username")
            url = account.get("url")
            verified = account.get("verified", False)

            if not service and not username:
                continue

            facts.append(
                NormalizedFact(
                    fact_type=FactType.SOCIAL_ACCOUNT,
                    value=username or str(url) or str(service),
                    source_connector=self.connector_name,
                    confidence=self._CONF_GRAVATAR_ACCOUNT,
                    metadata={
                        "field": "social_account",
                        "platform": service,
                        "url": url,
                        "verified": verified,
                        "source": "gravatar",
                    },
                )
            )

        return facts

    def _build_graph_relationships(
        self,
        email: str,
        domain: str,
        gravatar_profile: Optional[Dict[str, Any]],
    ) -> List[NormalizedFact]:
        """
        Build graph relationship edges.

        These are stored as SOCIAL_ACCOUNT facts with graph_edge=True
        metadata, consistent with how other normalizers create graph edges.
        """
        facts = []

        # Email → Domain relationship
        facts.append(
            NormalizedFact(
                fact_type=FactType.SOCIAL_ACCOUNT,
                value=f"{email} → domain:{domain}",
                source_connector=self.connector_name,
                confidence=self._CONF_GRAPH_EDGE,
                metadata={
                    "graph_edge": True,
                    "relationship": "uses_domain",
                    "from": email,
                    "from_type": "email",
                    "to": domain,
                    "to_type": "domain",
                },
            )
        )

        # Email → Gravatar relationship (if profile found)
        if gravatar_profile and isinstance(gravatar_profile, dict):
            gravatar_hash = gravatar_profile.get("hash")
            if gravatar_hash:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.SOCIAL_ACCOUNT,
                        value=f"{email} → gravatar:{gravatar_hash}",
                        source_connector=self.connector_name,
                        confidence=self._CONF_GRAPH_EDGE,
                        metadata={
                            "graph_edge": True,
                            "relationship": "has_gravatar",
                            "from": email,
                            "from_type": "email",
                            "to": f"gravatar:{gravatar_hash}",
                            "to_type": "gravatar",
                        },
                    )
                )

        return facts

    def _build_abstract_facts(self, rep: Dict[str, Any]) -> List[NormalizedFact]:
        """Extract data breach exposure, deliverability, domain age, and quality facts from Abstract API."""
        facts = []

        # 1. Data Breaches Exposure Summary & Individual Breached Platforms
        breaches_data = rep.get("email_breaches", {})
        total_breaches = breaches_data.get("total_breaches", 0)
        breached_domains = breaches_data.get("breached_domains", [])

        if total_breaches > 0:
            first_b = breaches_data.get("date_first_breached", "Unknown Date")
            last_b = breaches_data.get("date_last_breached", "Unknown Date")
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=f"Data Breach Exposure: {total_breaches} Breaches (First: {first_b}, Last: {last_b})",
                    source_connector=self.connector_name,
                    confidence=0.95,
                    metadata={
                        "field": "breach_count",
                        "total_breaches": total_breaches,
                        "date_first_breached": first_b,
                        "date_last_breached": last_b,
                    },
                )
            )

            for breach in breached_domains:
                if isinstance(breach, dict) and breach.get("domain"):
                    b_domain = breach.get("domain")
                    b_date = breach.get("breach_date", "Unknown Date")
                    url = f"https://{b_domain}" if "." in b_domain else None
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.SOCIAL_ACCOUNT,
                            value=f"{b_domain} (Breached: {b_date})",
                            source_connector=self.connector_name,
                            confidence=0.90,
                            metadata={
                                "platform": b_domain,
                                "platform_display_name": f"Breached Platform ({b_domain})",
                                "breach_date": b_date,
                                "profile_url": url,
                            },
                        )
                    )

        # 2. Email Reputation & Risk Status
        quality = rep.get("email_quality", {})
        score = quality.get("score")
        if score is not None:
            score_pct = int(score * 100)
            risk = rep.get("email_risk", {}).get("address_risk_status", "low")
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=f"Email Reputation Score: {score_pct}% ({risk.capitalize()} Risk)",
                    source_connector=self.connector_name,
                    confidence=0.90,
                    metadata={
                        "field": "reputation_score",
                        "score": score,
                        "risk_status": risk,
                    },
                )
            )

        # 3. Domain Registration Date & Registrar Details
        domain_info = rep.get("email_domain", {})
        reg_date = domain_info.get("date_registered")
        registrar = domain_info.get("registrar")
        if reg_date:
            reg_str = f" via {registrar}" if registrar else ""
            facts.append(
                NormalizedFact(
                    fact_type=FactType.GENERIC,
                    value=f"Registered on {reg_date}{reg_str}",
                    source_connector=self.connector_name,
                    confidence=0.95,
                    metadata={
                        "field": "domain_age",
                        "date_registered": reg_date,
                        "registrar": registrar,
                    },
                )
            )

        return facts
