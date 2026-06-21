"""Tests for document download endpoint."""

from __future__ import annotations

import uuid
from pathlib import Path
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


def _fake_document(file_url: str, original_filename: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        doc_type=SimpleNamespace(value="notice"),
        original_filename=original_filename,
        file_url=file_url,
        file_size=12,
        summary=None,
        status=SimpleNamespace(value="uploaded"),
        uploaded_by=uuid.uuid4(),
        uploaded_at=SimpleNamespace(isoformat=lambda: "2025-06-01T00:00:00+00:00"),
        processed_at=None,
    )


def _fake_db(document=None):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = document
    result_mock.scalar_one.return_value = document

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


def test_download_document_streams_file(client, tmp_path, monkeypatch):
    from app.database import get_db
    from app.routes import documents as documents_module

    monkeypatch.setattr(documents_module, "UPLOAD_DIR", tmp_path)

    doc_id = uuid.uuid4()
    file_path = tmp_path / f"{doc_id}.txt"
    file_path.write_text("hello world")

    document = _fake_document(str(file_path), "original.txt")
    app.dependency_overrides[get_db] = lambda: _fake_db(document=document)

    resp = client.get(f"/api/documents/{doc_id}/download")
    assert resp.status_code == 200
    assert resp.text == "hello world"
    assert resp.headers["content-disposition"].endswith('filename="original.txt"')

    app.dependency_overrides.pop(get_db, None)


def test_download_document_404_when_file_missing(client, tmp_path, monkeypatch):
    from app.database import get_db
    from app.routes import documents as documents_module

    monkeypatch.setattr(documents_module, "UPLOAD_DIR", tmp_path)

    doc_id = uuid.uuid4()
    document = _fake_document(str(tmp_path / f"{doc_id}.txt"), "missing.txt")
    app.dependency_overrides[get_db] = lambda: _fake_db(document=document)

    resp = client.get(f"/api/documents/{doc_id}/download")
    assert resp.status_code == 404

    app.dependency_overrides.pop(get_db, None)


def test_download_document_404_when_document_missing(client):
    from app.database import get_db

    app.dependency_overrides[get_db] = lambda: _fake_db(document=None)

    resp = client.get(f"/api/documents/{uuid.uuid4()}/download")
    assert resp.status_code == 404

    app.dependency_overrides.pop(get_db, None)
