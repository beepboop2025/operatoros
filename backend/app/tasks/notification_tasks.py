"""Outbound notification delivery — email (SMTP) and Telegram.

These run in the Celery worker, off the request path, so a slow or failed send never
touches the public signup. Each channel is configured independently and is skipped when
its settings are absent, so an unconfigured deploy is a clean no-op (the in-app bell
notification, written synchronously in the request, is unaffected either way).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from html import escape

import httpx

from app.celery_app import celery_app
from app.config import get_settings
from app.services.notification_service import PERSONA_LABELS

logger = logging.getLogger("operatoros.tasks.notifications")


def _send_email(subject: str, body: str) -> str:
    """Send a plain-text email via SMTP. Returns a short status string."""
    s = get_settings()
    if not (s.SMTP_HOST and s.NOTIFY_EMAIL_TO):
        return "skipped (SMTP not configured)"

    recipients = [addr.strip() for addr in s.NOTIFY_EMAIL_TO.split(",") if addr.strip()]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s.SMTP_FROM or s.SMTP_USER or "no-reply@operatoros"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=10) as server:
        if s.SMTP_USE_TLS:
            server.starttls()
        if s.SMTP_USER:
            server.login(s.SMTP_USER, s.SMTP_PASSWORD)
        server.send_message(msg)
    return f"sent to {len(recipients)} recipient(s)"


def _send_telegram(text: str) -> str:
    """Send a message via the Telegram Bot API. Returns a short status string."""
    s = get_settings()
    if not (s.TELEGRAM_BOT_TOKEN and s.TELEGRAM_CHAT_ID):
        return "skipped (Telegram not configured)"

    url = f"https://api.telegram.org/bot{s.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = httpx.post(
        url,
        json={"chat_id": s.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10,
    )
    resp.raise_for_status()
    return "sent"


@celery_app.task(bind=True, name="app.tasks.notification_tasks.deliver_signup_notification")
def deliver_signup_notification(
    self,
    email: str,
    name: str | None = None,
    persona: str | None = None,
    country: str | None = None,
    source: str | None = None,
) -> dict:
    """Deliver a "new signup" alert over every configured channel.

    Each channel is attempted independently and failures are logged (not raised), so one
    broken channel never blocks the other and the task does not retry-storm duplicate sends.
    """
    persona_label = PERSONA_LABELS.get(persona or "", persona)
    detail = ", ".join(p for p in (persona_label, country) if p)
    who = name or email

    subject = "New OperatorOS early-access signup"
    body = (
        f"{who} joined the waitlist.\n\n"
        f"Email:    {email}\n"
        f"Name:     {name or '—'}\n"
        f"Persona:  {persona_label or '—'}\n"
        f"Country:  {country or '—'}\n"
        f"Source:   {source or '—'}\n"
    )
    # parse_mode=HTML — escape every interpolated (user-supplied) value so a malicious
    # name/email/country can't inject markup or 400 the Telegram API. Literal tags stay.
    who_safe = escape(who)
    detail_safe = escape(detail)
    email_safe = escape(email)
    telegram_text = (
        f"🟢 <b>New OperatorOS signup</b>\n"
        f"{who_safe}" + (f" — {detail_safe}" if detail else "") + f"\n<code>{email_safe}</code>"
    )

    results: dict[str, str] = {}
    for channel, fn in (
        ("email", lambda: _send_email(subject, body)),
        ("telegram", lambda: _send_telegram(telegram_text)),
    ):
        try:
            results[channel] = fn()
        except Exception as exc:  # log and continue — best-effort, no retry storm
            logger.warning("Signup %s delivery failed for %s: %s", channel, email, exc)
            results[channel] = f"error: {exc}"

    logger.info("Signup delivery for %s: %s", email, results)
    return results
