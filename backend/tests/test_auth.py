"""Tests for authentication endpoints."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.middleware.auth import create_access_token


def _fake_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Test User",
        email="test@example.com",
        is_active=True,
        role=SimpleNamespace(value="associate"),
    )


def _fake_db(user=None):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    result_mock.scalar_one.return_value = user

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.flush = AsyncMock()
    session_mock.add = AsyncMock()
    return session_mock


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = _fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_refresh_token_returns_new_access_token(client):
    from app.database import get_db

    user = _fake_user()
    refresh_token = create_access_token({"sub": user.id, "role": user.role.value})

    app.dependency_overrides[get_db] = lambda: _fake_db(user=user)

    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == str(user.id)

    app.dependency_overrides.pop(get_db, None)


def test_refresh_token_rejects_invalid_token(client):
    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "not.a.valid.token"},
    )
    assert resp.status_code == 401


def test_refresh_token_rejects_inactive_user(client):
    from app.database import get_db

    user = _fake_user()
    user.is_active = False
    refresh_token = create_access_token({"sub": user.id, "role": user.role.value})

    app.dependency_overrides[get_db] = lambda: _fake_db(user=user)

    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 403

    app.dependency_overrides.pop(get_db, None)
