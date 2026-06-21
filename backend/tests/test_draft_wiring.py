"""Tests that draft/notices endpoints are wired to CommunicationDrafter."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.routes.draft import get_drafter
from app.routes.notices import get_drafter as notices_get_drafter


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


def _fake_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Test User",
        is_active=True,
        role=SimpleNamespace(value="associate"),
    )


def _fake_db(notice=None, client=None):
    """Return an async DB session mock that resolves the given ORM object."""
    resolved = notice or client

    from unittest.mock import MagicMock

    result_mock = MagicMock()
    # scalar_one_or_none() is a synchronous method on SQLAlchemy Result objects.
    result_mock.scalar_one_or_none.return_value = resolved
    result_mock.scalar_one.return_value = resolved

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.flush = AsyncMock()
    session_mock.add = AsyncMock()
    return session_mock


def _fake_notice():
    return SimpleNamespace(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        client=SimpleNamespace(
            firm_name="Acme Pvt Ltd",
            pan="AAACA1234A",
            gstin="07AAACA1234A1Z5",
            entity_type=SimpleNamespace(value="private_limited"),
        ),
        notice_type=SimpleNamespace(value="intimation_143_1"),
        notice_date=SimpleNamespace(isoformat=lambda: "2025-06-01"),
        response_deadline=SimpleNamespace(isoformat=lambda: "2025-06-30"),
        summary="Mismatch in 143(1) intimation",
    )


def _fake_client():
    return SimpleNamespace(
        id=uuid.uuid4(),
        firm_name="Acme Pvt Ltd",
        contact_person="John Doe",
        pan="AAACA1234A",
        entity_type=SimpleNamespace(value="private_limited"),
    )


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = _fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
#  Draft /response
# --------------------------------------------------------------------------- #


def test_draft_response_404_when_notice_missing(client):
    from app.database import get_db

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=None)

    resp = client.post(
        "/api/draft/response",
        json={"notice_id": str(uuid.uuid4()), "additional_context": ""},
    )
    assert resp.status_code == 404
    app.dependency_overrides.pop(get_db, None)


def test_draft_response_returns_llm_text(client):
    from app.database import get_db

    notice = _fake_notice()
    drafter_mock = AsyncMock()
    drafter_mock.draft_notice_response = AsyncMock(return_value="LLM-generated response text")

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=notice)
    app.dependency_overrides[get_drafter] = lambda: drafter_mock

    resp = client.post(
        "/api/draft/response",
        json={"notice_id": str(notice.id), "additional_context": "Extra context"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft_text"] == "LLM-generated response text"
    assert data["notice_id"] == str(notice.id)
    assert data["status"] == "draft_generated"

    drafter_mock.draft_notice_response.assert_awaited_once()

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_drafter, None)


def test_draft_response_503_on_llm_failure(client):
    from app.database import get_db

    notice = _fake_notice()
    drafter_mock = AsyncMock()
    drafter_mock.draft_notice_response = AsyncMock(side_effect=RuntimeError("LLM down"))

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=notice)
    app.dependency_overrides[get_drafter] = lambda: drafter_mock

    resp = client.post(
        "/api/draft/response",
        json={"notice_id": str(notice.id)},
    )
    assert resp.status_code == 503
    assert "LLM down" in resp.json()["detail"]

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_drafter, None)


# --------------------------------------------------------------------------- #
#  Draft /advisory
# --------------------------------------------------------------------------- #


def test_draft_advisory_returns_llm_text(client):
    from app.database import get_db

    client_obj = _fake_client()
    drafter_mock = AsyncMock()
    drafter_mock.draft_advisory = AsyncMock(return_value="LLM-generated advisory")

    app.dependency_overrides[get_db] = lambda: _fake_db(client=client_obj)
    app.dependency_overrides[get_drafter] = lambda: drafter_mock

    resp = client.post(
        "/api/draft/advisory",
        json={"client_id": str(client_obj.id), "topic": "80C planning", "context": "details"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["advisory_text"] == "LLM-generated advisory"
    assert data["topic"] == "80C planning"

    drafter_mock.draft_advisory.assert_awaited_once()

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_drafter, None)


def test_draft_advisory_503_on_llm_failure(client):
    from app.database import get_db

    client_obj = _fake_client()
    drafter_mock = AsyncMock()
    drafter_mock.draft_advisory = AsyncMock(side_effect=RuntimeError("LLM down"))

    app.dependency_overrides[get_db] = lambda: _fake_db(client=client_obj)
    app.dependency_overrides[get_drafter] = lambda: drafter_mock

    resp = client.post(
        "/api/draft/advisory",
        json={"client_id": str(client_obj.id), "topic": "80C"},
    )
    assert resp.status_code == 503

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_drafter, None)


# --------------------------------------------------------------------------- #
#  Draft /engagement-letter
# --------------------------------------------------------------------------- #


def test_draft_engagement_letter_returns_llm_text(client):
    from app.database import get_db

    client_obj = _fake_client()
    drafter_mock = AsyncMock()
    drafter_mock.draft_engagement_letter = AsyncMock(return_value="LLM-generated letter")

    app.dependency_overrides[get_db] = lambda: _fake_db(client=client_obj)
    app.dependency_overrides[get_drafter] = lambda: drafter_mock

    resp = client.post(
        "/api/draft/engagement-letter",
        json={"client_id": str(client_obj.id), "services": ["ITR filing"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["letter_text"] == "LLM-generated letter"
    assert data["services_included"] == ["ITR filing"]

    drafter_mock.draft_engagement_letter.assert_awaited_once()

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_drafter, None)


# --------------------------------------------------------------------------- #
#  Notices draft-response
# --------------------------------------------------------------------------- #


def test_notice_draft_response_returns_llm_text(client):
    from app.database import get_db

    notice = _fake_notice()
    drafter_mock = AsyncMock()
    drafter_mock.draft_notice_response = AsyncMock(return_value="LLM-generated notice reply")

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=notice)
    app.dependency_overrides[notices_get_drafter] = lambda: drafter_mock

    resp = client.post(f"/api/notices/{notice.id}/draft-response")
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft_text"] == "LLM-generated notice reply"
    assert data["notice_id"] == str(notice.id)

    drafter_mock.draft_notice_response.assert_awaited_once()

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(notices_get_drafter, None)


def test_notice_draft_response_503_on_llm_failure(client):
    from app.database import get_db

    notice = _fake_notice()
    drafter_mock = AsyncMock()
    drafter_mock.draft_notice_response = AsyncMock(side_effect=RuntimeError("LLM down"))

    app.dependency_overrides[get_db] = lambda: _fake_db(notice=notice)
    app.dependency_overrides[notices_get_drafter] = lambda: drafter_mock

    resp = client.post(f"/api/notices/{notice.id}/draft-response")
    assert resp.status_code == 503

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(notices_get_drafter, None)
