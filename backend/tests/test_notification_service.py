"""Tests for the notification service — in-app fan-out isolation and safe enqueue."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import notification_service as ns


class _CM:
    """Minimal async context manager yielding a given session (stands in for
    `async with async_session_factory() as session`)."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


# --------------------------------------------------------------------------- #
#  notify_staff — runs in its own session, one notification per active staffer
# --------------------------------------------------------------------------- #


async def test_notify_staff_creates_one_per_staff():
    staff = [SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())]
    result = MagicMock()
    result.scalars.return_value.all.return_value = staff

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()

    with patch.object(ns, "async_session_factory", lambda: _CM(session)):
        count = await ns.notify_staff(
            title="New signup", message="x", notification_type="waitlist_signup"
        )

    assert count == 2
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()


async def test_notify_staff_swallows_errors_and_never_raises():
    """A DB failure inside notify_staff must not propagate to the caller (the public
    signup must succeed even if notifications fail)."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))

    with patch.object(ns, "async_session_factory", lambda: _CM(session)):
        count = await ns.notify_staff(title="t", message="m")

    assert count == 0  # returned cleanly, no exception


# --------------------------------------------------------------------------- #
#  enqueue_signup_delivery — broker-failure-safe
# --------------------------------------------------------------------------- #


def test_enqueue_signup_delivery_returns_true_on_success():
    fake_task = MagicMock()
    with patch("app.tasks.notification_tasks.deliver_signup_notification", fake_task):
        ok = ns.enqueue_signup_delivery(email="a@b.com", name="A", persona="nri")
    assert ok is True
    fake_task.delay.assert_called_once()


def test_enqueue_signup_delivery_returns_false_when_broker_unreachable():
    fake_task = MagicMock()
    fake_task.delay.side_effect = RuntimeError("broker down")
    with patch("app.tasks.notification_tasks.deliver_signup_notification", fake_task):
        ok = ns.enqueue_signup_delivery(email="a@b.com")
    assert ok is False  # swallowed — never raises into the request path


# --------------------------------------------------------------------------- #
#  create_notification — adds a row to the caller's session
# --------------------------------------------------------------------------- #


def test_create_notification_adds_to_session():
    session = MagicMock()
    notification = ns.create_notification(
        session, user_id=uuid.uuid4(), title="T", message="M", notification_type="waitlist_signup"
    )
    session.add.assert_called_once_with(notification)
    assert notification.title == "T"
    assert notification.message == "M"
    assert notification.notification_type == "waitlist_signup"
