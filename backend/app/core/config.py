"""
Application configuration.

Loads settings from environment variables (see .env.example). This module
defines ONLY the configuration surface needed by the skeleton: app metadata,
API prefix, and PostgreSQL connection settings. It intentionally does not
define anything related to models, connectors, auth, or Neo4j — those are
out of scope for this piece of the project (see MASTER_DESIGN.md).
"""

import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "OSINT Intelligence Aggregator"
    app_env: str = "development"
    debug: bool = True

    # --- API ---
    api_v1_prefix: str = "/api/v1"

    # --- PostgreSQL ---
    postgres_user: str = "osint_user"
    postgres_password: str = "change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "osint_aggregator"

    # If not explicitly provided via env, this is assembled from the
    # POSTGRES_* fields above in the `database_url` property below.
    database_url: str | None = None

    # --- JWT Auth ---
    jwt_secret_key: str = "CHANGE-THIS-IN-PRODUCTION-USE-A-LONG-RANDOM-STRING"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- OTP ---
    otp_expire_minutes: int = 5

    # --- EmailJS ---
    emailjs_service_id: str = ""
    emailjs_template_id: str = ""
    emailjs_public_key: str = ""
    emailjs_private_key: str = ""
    # --- Truecaller RapidAPI ---
    truecaller_rapidapi_key: str = ""
    truecaller_rapidapi_host: str = "truecaller-data2.p.rapidapi.com"

    # --- Abstract Email Reputation API ---
    abstract_api_key: str = "960cfb8915eb402c961657d4fc422e7e"

    # --- VirusTotal v3 API ---
    virustotal_api_key: str = ""

    # --- GitHub REST API ---
    github_token: str = ""

    # --- DigiFootprint API ---
    digifootprint_api_key: str = "dfp_e322916d5de5f61fba35a2df6c19f45d76e517eb6a27292cfeafac46bf8924bf"



    @property
    def sqlalchemy_database_url(self) -> str:
        """Return the connection string SQLAlchemy should use.

        Prefers an explicitly-set DATABASE_URL, falling back to a URL
        assembled from the individual POSTGRES_* settings.
        """
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (avoids re-parsing env on every call)."""
    return Settings()


def validate_config():
    """Validate required configuration at startup."""
    settings = get_settings()
    errors = []

    if not settings.sqlalchemy_database_url:
        errors.append("Database URL configuration is invalid")

    if errors:
        print("Configuration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
