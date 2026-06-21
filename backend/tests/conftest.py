"""Shared pytest fixtures and helpers for OperatorOS backend tests."""

from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Ensure each test starts with a fresh settings instance."""
    get_settings.cache_clear()
