"""Tests for World Tax Radar tax-intel endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.dependencies import get_current_user, get_current_user_optional
from app.main import app


def _fake_user(role="admin"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Test User",
        is_active=True,
        role=SimpleNamespace(value=role),
    )


def _fake_db_for_add(item=None):
    """Mock DB whose flush populates server-side defaults (id, created_at) on the
    object passed to add(), mirroring what the real database does on flush."""
    captured = {}

    def _add(obj):
        captured["obj"] = obj

    async def _flush():
        obj = captured.get("obj")
        if obj is not None:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)

    session_mock = AsyncMock()
    session_mock.add = MagicMock(side_effect=_add)
    session_mock.flush = AsyncMock(side_effect=_flush)
    return session_mock


def _fake_db_for_list(items, total):
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = total
    result_mock.scalars.return_value.all.return_value = items

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.flush = AsyncMock()
    session_mock.add = MagicMock()
    return session_mock


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ingest_tax_intel_with_admin_token(client):
    from app.database import get_db
    from app.models.tax_intel import TaxIntel

    item = TaxIntel(
        id=uuid.uuid4(),
        title="India-UAE DTAA update",
        source_url="https://example.com/news",
        jurisdiction="UAE",
        topic="DTAA",
        nri_impact_score=75,
        matched_terms=["DTAA", "UAE"],
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user_optional] = lambda: _fake_user("admin")
    app.dependency_overrides[get_db] = lambda: _fake_db_for_add(item)

    resp = client.post(
        "/api/tax-intel/ingest",
        json={
            "title": "India-UAE DTAA update",
            "summary": "New protocol signed.",
            "source_url": "https://example.com/news",
            "jurisdiction": "UAE",
            "topic": "DTAA",
            "nri_impact_score": 75,
            "matched_terms": ["DTAA", "UAE"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "India-UAE DTAA update"

    app.dependency_overrides.pop(get_db, None)


def test_ingest_tax_intel_with_api_key(client):
    from app.database import get_db
    from app.models.tax_intel import TaxIntel

    item = TaxIntel(
        id=uuid.uuid4(),
        title="India-UAE DTAA update",
        source_url="https://example.com/news",
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_db] = lambda: _fake_db_for_add(item)
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(INGEST_API_KEY="secret-key")

    resp = client.post(
        "/api/tax-intel/ingest",
        headers={"X-API-Key": "secret-key"},
        json={
            "title": "India-UAE DTAA update",
            "source_url": "https://example.com/news",
        },
    )
    assert resp.status_code == 201

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_settings, None)


def test_ingest_tax_intel_rejects_unauthorized(client):
    resp = client.post(
        "/api/tax-intel/ingest",
        json={"title": "Test", "source_url": "https://example.com"},
    )
    assert resp.status_code == 401


def test_list_tax_intel_returns_paginated_items(client):
    from app.database import get_db
    from app.models.tax_intel import TaxIntel

    item = TaxIntel(
        id=uuid.uuid4(),
        title="India-UAE DTAA update",
        source_url="https://example.com/news",
        jurisdiction="UAE",
        topic="DTAA",
        nri_impact_score=75,
        matched_terms=["DTAA"],
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_db] = lambda: _fake_db_for_list([item], 1)

    resp = client.get("/api/tax-intel?jurisdiction=UAE")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["jurisdiction"] == "UAE"

    app.dependency_overrides.pop(get_db, None)
