"""Tests for notice response submission."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
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


def _fake_notice():
    return SimpleNamespace(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        client=SimpleNamespace(firm_name="Acme Pvt Ltd"),
        notice_type=SimpleNamespace(value="intimation_143_1"),
        notice_date=date(2025, 6, 1),
        response_deadline=None,
        summary="Mismatch in 143(1) intimation",
        status=SimpleNamespace(value="response_drafted"),
        assigned_to=None,
        document_id=None,
        created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


def _fake_db(notice=None):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = notice
    result_mock.scalar_one.return_value = notice

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


def test_submit_response_updates_notice(client):
    from app.database import get_db

    user = _fake_user()
    notice = _fake_notice()
    notice.assigned_to = user.id
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: _fake_db(notice=notice)

    resp = client.post(
        f"/api/notices/{notice.id}/submit-response",
        json={"response_text": "Filed response attached."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "response_filed"
    assert notice.filed_response == "Filed response attached."

    app.dependency_overrides.pop(get_db, None)


def test_submit_response_404_when_notice_missing(client):
    from app.database import get_db

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=None)

    resp = client.post(
        f"/api/notices/{uuid.uuid4()}/submit-response",
        json={"response_text": "Filed response attached."},
    )
    assert resp.status_code == 404

    app.dependency_overrides.pop(get_db, None)
