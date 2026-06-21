"""Unit tests for TDS computation."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.tax_engine import TDSRequest, compute_tds


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def test_tds_section_194c_above_threshold(tds_request_factory):
    req = tds_request_factory(section="194C", payment_amount=D("50_000"))
    resp = compute_tds(req)
    assert resp.section == "194C"
    assert resp.applicable_rate == D("0.01")
    assert resp.tds_amount == D("500")
    assert "contractor" in resp.description.lower()


def test_tds_section_194c_below_threshold(tds_request_factory):
    req = tds_request_factory(section="194C", payment_amount=D("25_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D(0)
    assert resp.tds_amount == D(0)
    assert resp.threshold == D("30_000")


def test_tds_section_194c_no_pan(tds_request_factory):
    req = tds_request_factory(section="194C", payment_amount=D("50_000"), has_pan=False)
    resp = compute_tds(req)
    # 206AA: max(20%, 2x1%) = 20%
    assert resp.applicable_rate == D("0.20")
    assert resp.tds_amount == D("10_000")


def test_tds_section_194c_other_recipient(tds_request_factory):
    req = tds_request_factory(
        section="194C", payment_amount=D("100_000"), recipient_type="company"
    )
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.02")
    assert resp.tds_amount == D("2_000")


def test_tds_section_194j_professional(tds_request_factory):
    req = tds_request_factory(section="194J(b)", payment_amount=D("100_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.10")
    assert resp.tds_amount == D("10_000")


def test_tds_section_194j_technical(tds_request_factory):
    req = tds_request_factory(section="194J(a)", payment_amount=D("100_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.02")
    assert resp.tds_amount == D("2_000")


def test_tds_section_194a_non_senior(tds_request_factory):
    req = tds_request_factory(
        section="194A", payment_amount=D("50_000"), is_senior_citizen=False
    )
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.10")
    assert resp.tds_amount == D("5_000")


def test_tds_section_194a_senior_below_threshold(tds_request_factory):
    req = tds_request_factory(
        section="194A", payment_amount=D("45_000"), is_senior_citizen=True
    )
    resp = compute_tds(req)
    assert resp.applicable_rate == D(0)
    assert resp.tds_amount == D(0)


def test_tds_section_194a_senior_above_threshold(tds_request_factory):
    """Current engine applies rate on full amount; threshold excess logic is a known gap."""
    req = tds_request_factory(
        section="194A", payment_amount=D("60_000"), is_senior_citizen=True
    )
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.10")
    assert resp.tds_amount == D("6_000")


def test_tds_section_192_salary_at_slabs(tds_request_factory):
    req = tds_request_factory(section="192", payment_amount=D("500_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D(0)
    assert resp.tds_amount == D(0)
    assert "slab" in resp.notes.lower()


def test_tds_section_194b_winnings(tds_request_factory):
    req = tds_request_factory(section="194B", payment_amount=D("100_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.30")
    assert resp.tds_amount == D("30_000")


def test_tds_section_194ia_property(tds_request_factory):
    """Engine applies rate on full consideration once threshold is crossed."""
    req = tds_request_factory(section="194IA", payment_amount=D("6_000_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.01")
    assert resp.tds_amount == D("60_000")
    assert resp.threshold == D("5_000_000")


def test_tds_section_194q_goods(tds_request_factory):
    req = tds_request_factory(section="194Q", payment_amount=D("6_000_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.001")
    assert resp.tds_amount == D("6_000")


def test_tds_threshold_boundary(tds_request_factory):
    # 194C threshold is ₹30,000 per single payment.
    below = tds_request_factory(section="194C", payment_amount=D("29_999.99"))
    above = tds_request_factory(section="194C", payment_amount=D("30_000"))
    assert compute_tds(below).tds_amount == D(0)
    assert compute_tds(above).tds_amount == D("300")


def test_tds_unknown_section(tds_request_factory):
    req = tds_request_factory(section="999Z", payment_amount=D("100_000"))
    resp = compute_tds(req)
    assert resp.tds_amount == D(0)
    assert "no tds rate entry" in resp.notes.lower()


def test_tds_no_pan_floor_is_20_percent_for_tds(tds_request_factory):
    # 194Q is a TDS section; 206AA floor is 20%.
    req = tds_request_factory(section="194Q", payment_amount=D("6_000_000"), has_pan=False)
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.20")
    assert resp.tds_amount == D("1_200_000")


# TCS sanity checks
def test_tcs_section_206c_1f_vehicle(tds_request_factory):
    req = tds_request_factory(section="206C(1F)", payment_amount=D("1_200_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.01")
    assert resp.tds_amount == D("12_000")


def test_tcs_section_206c_1h_goods(tds_request_factory):
    req = tds_request_factory(section="206C(1H)", payment_amount=D("6_000_000"))
    resp = compute_tds(req)
    assert resp.applicable_rate == D("0.001")
    assert resp.tds_amount == D("6_000")
