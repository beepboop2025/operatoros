"""Tests for application settings and startup validation."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_redis_url_without_password() -> None:
    """When REDIS_PASSWORD is empty, Redis URLs keep their plain form."""
    settings = Settings(REDIS_URL="redis://redis:6379/0", REDIS_PASSWORD="")
    assert settings.REDIS_URL == "redis://redis:6379/0"
    assert settings.CELERY_BROKER_URL == "redis://redis:6379/0"
    assert settings.CELERY_RESULT_BACKEND == "redis://redis:6379/0"


def test_redis_url_with_password() -> None:
    """When REDIS_PASSWORD is set, it is injected into all Redis URLs."""
    settings = Settings(
        REDIS_URL="redis://redis:6379/0",
        REDIS_PASSWORD="secret123",
        CELERY_BROKER_URL="redis://redis:6379/0",
        CELERY_RESULT_BACKEND="redis://redis:6379/0",
    )
    assert settings.REDIS_URL == "redis://:secret123@redis:6379/0"
    assert settings.CELERY_BROKER_URL == "redis://:secret123@redis:6379/0"
    assert settings.CELERY_RESULT_BACKEND == "redis://:secret123@redis:6379/0"


def test_redis_password_preserved_across_non_default_port() -> None:
    """Password injection works for Redis URLs with a custom port."""
    settings = Settings(
        REDIS_URL="redis://redis:6380/1",
        REDIS_PASSWORD="supersecure",
    )
    assert settings.REDIS_URL == "redis://:supersecure@redis:6380/1"


def test_no_usable_llm_provider_raises() -> None:
    """Validation fails fast when no LLM provider is configured."""
    with pytest.raises(ValidationError, match="No usable LLM provider"):
        Settings(FREE_LLM_ENABLED=False, OPENROUTER_API_KEY="")


def test_free_llm_enabled_without_keys_is_allowed() -> None:
    """Enabling the free router without provider keys is allowed at config time."""
    settings = Settings(FREE_LLM_ENABLED=True, OPENROUTER_API_KEY="")
    assert settings.FREE_LLM_ENABLED is True


def test_openrouter_key_alone_is_allowed() -> None:
    """Using only OpenRouter is a valid configuration."""
    settings = Settings(FREE_LLM_ENABLED=False, OPENROUTER_API_KEY="sk-or-test")
    assert settings.OPENROUTER_API_KEY == "sk-or-test"


def test_get_settings_cached() -> None:
    """get_settings returns a cached singleton."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
