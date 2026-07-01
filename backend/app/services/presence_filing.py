"""
Presence-filing service — OTP-gated *execution* of computed returns.

OperatorOS computes returns (tax_engine / compliance_engine); historically a human
then logs into the GST / Income-Tax portal, receives an OTP on their phone, and
submits by hand. This service automates that last mile via the **Presence Layer**
(github.com/beepboop2025/farmctl, ``presence/``): a farm of real Indian-SIM devices
that can receive the portal OTP and complete the login + submission.

This is what moves OperatorOS from *advice* to *execution*.

Legal guardrail
---------------
Indian portals are OTP/mobile-gated and their terms restrict automation. This path
is intended ONLY for a firm automating its **own staff's filing actions for its own
consenting clients** — the same actions staff already perform by hand. It is:

  * **dry-run by default** — authenticates + validates but does NOT submit unless the
    caller passes ``confirm=True`` (two explicit opt-ins);
  * **blocked from real portals** unless ``PRESENCE_ALLOW_REAL=1`` is set in the env;
  * **fully audited** (hash-chained trail returned with every call).

Until a real ``AppPortalDriver`` recipe is wired for a specific portal, this service
runs against the Presence Layer's mock portal so the flow is exercisable end-to-end.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# The Presence Layer ships in the farmctl repo; import it, adding the local checkout
# to sys.path if it isn't installed (mirrors how aide locates free-llm-router).
_PRESENCE_PATHS = [os.path.expanduser("~/farmctl")]


def _load_presence():
    try:
        import presence  # noqa: F401
    except ImportError:
        for p in _PRESENCE_PATHS:
            if os.path.isdir(os.path.join(p, "presence")) and p not in sys.path:
                sys.path.insert(0, p)
    from presence import (  # type: ignore
        Identity, FilingOrchestrator, HttpPortal, MockSmsOtpSource, Filing,
    )
    return Identity, FilingOrchestrator, HttpPortal, MockSmsOtpSource, Filing


class PresenceFilingService:
    """Bridges a computed OperatorOS return to an OTP-gated portal submission."""

    @staticmethod
    def file_return(
        *,
        form_type: str,
        period: str,
        payload: Dict[str, Any],
        portal_url: str,
        identity_id: str,
        msisdn: str,
        sms_inbox: str,
        pan: Optional[str] = None,
        confirm: bool = False,
        dry_run: bool = True,
        otp_timeout: float = 60.0,
        sender_hint: str = "INCMTAX",
    ) -> Dict[str, Any]:
        """Authenticate via OTP and (optionally) submit ``payload`` for ``form_type``.

        Returns a dict with ``ok``, ``receipt`` and the hash-chained ``audit`` trail,
        suitable for returning straight to an API caller.

        ``portal_url`` should be the mock portal in the prototype; a real REST portal
        requires ``PRESENCE_ALLOW_REAL=1`` (enforced inside the Presence Layer).
        ``sms_inbox`` is the mock SMS file; the production path swaps ``MockSmsOtpSource``
        for ``AdbSmsOtpSource(endpoint=...)`` reading a real device's inbox.
        """
        Identity, FilingOrchestrator, HttpPortal, MockSmsOtpSource, Filing = _load_presence()

        ident = Identity(id=identity_id, msisdn=msisdn, region="IN",
                         persona={"pan": pan or identity_id})
        portal = HttpPortal(portal_url)
        otp_source = MockSmsOtpSource(sms_inbox)
        filing = Filing(form_type=form_type, period=period, payload=payload)

        logger.info("presence filing %s/%s via %s (dry_run=%s, confirm=%s)",
                    form_type, period, identity_id, dry_run, confirm)

        result = FilingOrchestrator(dry_run=dry_run).file_return(
            identity=ident, portal=portal, otp_source=otp_source, filing=filing,
            confirm=confirm, otp_timeout=otp_timeout, sender_hint=sender_hint,
        )
        return {
            "ok": result.ok,
            "message": result.message,
            "receipt": result.receipt.__dict__ if result.receipt else None,
            "audit": result.audit,
        }
