"""Tests for the free-llm-router provider ordering policy."""

from __future__ import annotations

import pytest

from free_llm_router.policy import smart_order
from free_llm_router.providers import Provider
from free_llm_router.router import ProviderStats


def _make_provider(name: str, priority: int) -> Provider:
    return Provider(
        name=name,
        base_url="https://example.com",
        api_key_env=f"{name.upper()}_KEY",
        models={"fast": "model", "smart": "model"},
        rpm=10,
        rpd=100,
        priority=priority,
    )


def test_smart_order_prefers_healthy_circuits():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    stats = [
        ProviderStats(groq, "open", True, 0, 100, 0.0),
        ProviderStats(cerebras, "closed", True, 0, 100, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["cerebras", "groq"]


def test_smart_order_prefers_available_tokens():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    stats = [
        ProviderStats(groq, "closed", True, 0, 100, 0.0),
        ProviderStats(cerebras, "closed", False, 0, 100, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["groq", "cerebras"]


def test_smart_order_prefers_more_quota_headroom():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    stats = [
        ProviderStats(groq, "closed", True, 90, 100, 0.0),
        ProviderStats(cerebras, "closed", True, 10, 100, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["cerebras", "groq"]


def test_smart_order_treats_unknown_quota_as_unlimited():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    stats = [
        ProviderStats(groq, "closed", True, 10, 100, 0.0),
        ProviderStats(cerebras, "closed", True, 0, None, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["cerebras", "groq"]


def test_smart_order_uses_static_priority_as_tiebreaker():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    stats = [
        ProviderStats(cerebras, "closed", True, 0, 100, 0.0),
        ProviderStats(groq, "closed", True, 0, 100, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["groq", "cerebras"]


def test_smart_order_all_factors_together():
    groq = _make_provider("groq", priority=10)
    cerebras = _make_provider("cerebras", priority=20)
    google = _make_provider("google", priority=30)
    mistral = _make_provider("mistral", priority=40)

    stats = [
        # open circuit, should be last
        ProviderStats(mistral, "open", True, 0, 100, 0.0),
        # closed but no tokens
        ProviderStats(cerebras, "closed", False, 0, 100, 0.0),
        # closed, tokens, but more quota used
        ProviderStats(google, "closed", True, 80, 100, 0.0),
        # best overall
        ProviderStats(groq, "closed", True, 5, 100, 0.0),
    ]
    ordered = smart_order(stats)
    assert [p.name for p in ordered] == ["groq", "google", "cerebras", "mistral"]
