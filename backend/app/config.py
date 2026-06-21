"""
OperatorOS application settings.

Reads from environment variables (or .env file) using pydantic-settings.
Access the singleton via ``get_settings()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, List
from urllib.parse import urlparse, urlunparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://operatoros:operatoros@postgres:5432/operatoros"

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: str = ""

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-random-64-char-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── AI / LLM ─────────────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    DEFAULT_LLM_MODEL: str = "anthropic/claude-sonnet-4.6"
    # Force a single model across all task routing (blank = use per-task routing).
    # Set to a free model (e.g. "meta-llama/llama-3.3-70b-instruct:free") on deploys
    # without OpenRouter credits.
    LLM_MODEL_OVERRIDE: str = ""

    # ── Free LLM router (perpetually-free providers) ───────────────────────────
    # When true, low-stakes task types (classification/factual/bulk) are served by
    # free providers first, falling back to paid OpenRouter only if all free
    # providers fail. High-stakes advisory/drafting always prefers paid for quality.
    FREE_LLM_ENABLED: bool = True
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    GOOGLE_AI_STUDIO_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""

    # ── n8n ──────────────────────────────────────────────────────────────────
    N8N_WEBHOOK_URL: str = "http://n8n:5678"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # NoDecode: stop pydantic-settings (2.x) from JSON-decoding this List field at the
    # env-source layer, so the comma-separated .env value reaches parse_cors_origins().
    # Without it, `CORS_ORIGINS=a,b` crashes settings load on a fresh build (pydantic-settings >= ~2.7).
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # ── PDF ────────────────────────────────────────────────────────────────
    PDF_OUTPUT_DIR: str = "/app/reports"

    # ── Ingest / scraper security ────────────────────────────────────────────
    INGEST_API_KEY: str = ""

    # ── Notifications — outbound delivery ─────────────────────────────────────
    # All optional. A channel is only used when its settings are present, so an
    # unconfigured deploy silently no-ops (in-app bell notifications still work).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""           # falls back to SMTP_USER when empty
    SMTP_USE_TLS: bool = True
    NOTIFY_EMAIL_TO: str = ""     # recipient(s) for signup/ops alerts; comma-separated
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Application ──────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Reject the default placeholder key in non-development environments."""
        if v == "change-me-to-random-64-char-string":
            import os
            env = os.getenv("ENVIRONMENT", "development")
            if env != "development":
                raise ValueError(
                    "SECRET_KEY must be changed from the default value in production. "
                    "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        return v

    @field_validator("OPENROUTER_API_KEY", mode="after")
    @classmethod
    def validate_openrouter_key(cls, v: str) -> str:
        """Warn if OpenRouter API key is empty."""
        if not v:
            import logging
            logging.getLogger("operatoros.config").warning(
                "OPENROUTER_API_KEY is empty — AI/LLM features will not work"
            )
        return v

    @model_validator(mode="after")
    def inject_redis_password(self) -> "Settings":
        """Embed REDIS_PASSWORD into Redis/Celery URLs when one is supplied."""
        if self.REDIS_PASSWORD:
            self.REDIS_URL = self._redis_url_with_password(self.REDIS_URL)
            self.CELERY_BROKER_URL = self._redis_url_with_password(self.CELERY_BROKER_URL)
            self.CELERY_RESULT_BACKEND = self._redis_url_with_password(self.CELERY_RESULT_BACKEND)
        return self

    @model_validator(mode="after")
    def validate_usable_llm_provider(self) -> "Settings":
        """Fail fast if no LLM provider is usable."""
        if not self.FREE_LLM_ENABLED and not self.OPENROUTER_API_KEY:
            raise ValueError(
                "No usable LLM provider: FREE_LLM_ENABLED is false and OPENROUTER_API_KEY is empty. "
                "Set OPENROUTER_API_KEY or enable the free LLM router and provide at least one provider key."
            )
        return self

    def _redis_url_with_password(self, url: str) -> str:
        """Return a Redis URL with the configured password inserted."""
        parsed = urlparse(url)
        # netloc is built as [user[:password]@]host[:port]
        userinfo = f":{self.REDIS_PASSWORD}" if self.REDIS_PASSWORD else ""
        netloc = f"{userinfo}@{parsed.hostname or 'redis'}"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
