"""Tests for notification endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


def _fake_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Test User",
        is_active=True,
        role=SimpleNamespace(value="associate"),
    )


def _fake_notification(user_id, is_read=False):
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        title="New notice",
        message="A notice has been received.",
        notification_type="notice",
        entity_type="notice",
        entity_id=uuid.uuid4(),
        is_read=is_read,
        created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        read_at=None,
    )


def _fake_db_for_list(notifications):
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = notifications

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.flush = AsyncMock()
    session_mock.add = AsyncMock()
    return session_mock


def _fake_db_for_get(notification):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = notification

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


def test_list_unread_notifications(client):
    from app.database import get_db

    user = _fake_user()
    notification = _fake_notification(user.id)
    app.dependency_overrides[get_db] = lambda: _fake_db_for_list([notification])

    resp = client.get("/api/notifications/unread")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "New notice"
    assert data[0]["is_read"] is False

    app.dependency_overrides.pop(get_db, None)


def test_mark_notification_read(client):
    from app.database import get_db

    user = _fake_user()
    notification = _fake_notification(user.id)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: _fake_db_for_get(notification)

    resp = client.post(f"/api/notifications/{notification.id}/mark-read")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True
    assert notification.is_read is True
    assert notification.read_at is not None

    app.dependency_overrides.pop(get_db, None)


def test_mark_notification_read_404_for_other_user(client):
    from app.database import get_db

    other_user_id = uuid.uuid4()
    notification = _fake_notification(other_user_id)
    app.dependency_overrides[get_db] = lambda: _fake_db_for_get(notification)

    resp = client.post(f"/api/notifications/{notification.id}/mark-read")
    assert resp.status_code == 404

    app.dependency_overrides.pop(get_db, None)
