"""Tests for the public waitlist endpoints (create, idempotency, CSV export)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.main import app
from app.routes.waitlist import _csv_safe


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_user(role: str = "admin"):
    return SimpleNamespace(
        id=uuid.uuid4(), full_name="Admin", is_active=True, role=SimpleNamespace(value=role)
    )


def _db_new_entry():
    """Mock session: no existing row; flush populates id/created_at on the added object."""
    captured: dict = {}

    def _add(obj):
        captured["obj"] = obj

    async def _flush():
        obj = captured.get("obj")
        if obj is not None:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)  # no existing entry
    session.add = MagicMock(side_effect=_add)
    session.flush = AsyncMock(side_effect=_flush)
    return session


# --------------------------------------------------------------------------- #
#  POST /api/waitlist/
# --------------------------------------------------------------------------- #


@patch("app.routes.waitlist.enqueue_signup_delivery", new=MagicMock())
@patch("app.routes.waitlist.notify_staff", new=AsyncMock())
def test_join_waitlist_creates_entry(client):
    session = _db_new_entry()
    app.dependency_overrides[get_db] = lambda: session

    resp = client.post(
        "/api/waitlist/",
        json={"email": "Demo@Example.com", "name": "Vikram", "persona": "nri", "country": "USA"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "demo@example.com"  # normalised (lowercased/stripped)
    assert data["persona"] == "nri"
    session.add.assert_called_once()  # a new row was inserted


@patch("app.routes.waitlist.enqueue_signup_delivery", new=MagicMock())
@patch("app.routes.waitlist.notify_staff", new=AsyncMock())
def test_join_waitlist_is_idempotent_on_email(client):
    existing = SimpleNamespace(
        id=uuid.uuid4(), email="demo@example.com", name="Existing", persona="nri",
        country="USA", source="landing", created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=existing)
    session.add = MagicMock()
    session.flush = AsyncMock()
    app.dependency_overrides[get_db] = lambda: session

    resp = client.post("/api/waitlist/", json={"email": "demo@example.com"})

    assert resp.status_code == 201
    assert resp.json()["email"] == "demo@example.com"
    session.add.assert_not_called()  # no duplicate row created


# --------------------------------------------------------------------------- #
#  GET /api/waitlist/  and  /export.csv  (admin-only)
# --------------------------------------------------------------------------- #


def test_list_waitlist_requires_auth(client):
    resp = client.get("/api/waitlist/")
    assert resp.status_code in (401, 403)


def test_export_csv_requires_auth(client):
    resp = client.get("/api/waitlist/export.csv")
    assert resp.status_code in (401, 403)


def test_export_csv_returns_csv_and_neutralises_injection(client):
    entry = SimpleNamespace(
        email="a@b.com", name="=HYPERLINK(0)", persona="nri", country="USA",
        source="hero", created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [entry]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user_optional] = lambda: _fake_user("admin")

    resp = client.get("/api/waitlist/export.csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    body = resp.text
    assert "email,name,persona,country,source,created_at" in body
    assert "'=HYPERLINK(0)" in body          # formula-injection neutralised
    assert "NRI" in body                      # persona humanised


# --------------------------------------------------------------------------- #
#  _csv_safe unit tests
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,expected",
    [
        ("=cmd|calc", "'=cmd|calc"),
        ("+1-555", "'+1-555"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\ttabbed", "'\ttabbed"),
        ("normal text", "normal text"),
        ("user@example.com", "user@example.com"),
        (None, ""),
    ],
)
def test_csv_safe(value, expected):
    assert _csv_safe(value) == expected
