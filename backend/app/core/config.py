"""
app/core/config.py
==================
Centralised application settings loaded from environment variables or a
`.env` file via Pydantic Settings.  Every secret and runtime knob lives
here — no hardcoded values anywhere else in the codebase.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables.

    Pydantic Settings automatically reads from:
    1. Environment variables (highest priority)
    2. The `.env` file in the working directory
    3. Field default values (lowest priority)

    ``case_sensitive=True`` prevents accidental shadowing by lower-cased
    environment variables on case-insensitive operating systems.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        # Allow extra fields that may appear in .env without raising an error
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Project metadata
    # ------------------------------------------------------------------
    PROJECT_NAME: str = "AgentOps Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # Runtime environment
    # ------------------------------------------------------------------
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        ...,
        description=(
            "Async PostgreSQL DSN, e.g. "
            "postgresql+asyncpg://user:pass@host:5432/dbname"
        ),
    )

    # ------------------------------------------------------------------
    # Redis / Celery broker
    # ------------------------------------------------------------------
    REDIS_URL: str = Field(
        ...,
        description="Redis DSN used as Celery broker and result backend.",
    )

    # ------------------------------------------------------------------
    # Auth – JWT
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="HMAC secret for signing JWT tokens. Must be 32+ chars.",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = Field(
        ...,
        description="Stripe secret API key (sk_live_... or sk_test_...).",
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        ...,
        description="Stripe webhook signing secret (whsec_...).",
    )


# ---------------------------------------------------------------------------
# Module-level singleton — import ``settings`` everywhere instead of
# instantiating Settings() multiple times.
# ---------------------------------------------------------------------------
settings = Settings()  # type: ignore[call-arg]  # values come from env
