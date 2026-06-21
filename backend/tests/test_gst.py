"""Unit tests for GST computation."""
from __future__ import annotations

from decimal import Decimal

from app.services.tax_engine import GSTRequest, compute_gst


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def test_gst_intra_state_18_percent(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("100_000"),
        gst_rate=D("0.18"),
        place_of_origin_state="Karnataka",
        place_of_supply_state="Karnataka",
    )
    resp = compute_gst(req)
    assert resp.gst_rate == D("0.18")
    assert resp.is_inter_state is False
    assert resp.cgst == D("9_000")
    assert resp.sgst == D("9_000")
    assert resp.igst == D(0)
    assert resp.total_gst == D("18_000")
    assert resp.invoice_total == D("118_000")


def test_gst_inter_state_18_percent(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("100_000"),
        gst_rate=D("0.18"),
        place_of_origin_state="Karnataka",
        place_of_supply_state="Maharashtra",
    )
    resp = compute_gst(req)
    assert resp.is_inter_state is True
    assert resp.cgst == D(0)
    assert resp.sgst == D(0)
    assert resp.igst == D("18_000")
    assert resp.total_gst == D("18_000")
    assert resp.invoice_total == D("118_000")


def test_gst_intra_state_rounding(gst_request_factory):
    # 5% rate split evenly; ₹1,000 * 5% = 50, so CGST/SGST are exact.
    req = gst_request_factory(
        taxable_value=D("1_000"),
        gst_rate=D("0.05"),
        place_of_origin_state="Delhi",
        place_of_supply_state="Delhi",
    )
    resp = compute_gst(req)
    assert resp.total_gst == D("50")
    assert resp.cgst == D("25")
    assert resp.sgst == D("25")
    assert resp.cgst + resp.sgst == resp.total_gst


def test_gst_hsn_lookup(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("50_000"),
        hsn_sac="998311",
        place_of_origin_state="Tamil Nadu",
        place_of_supply_state="Tamil Nadu",
    )
    resp = compute_gst(req)
    assert resp.gst_rate == D("0.18")
    assert resp.hsn_sac == "998311"
    assert "software" in resp.description.lower()
    assert resp.total_gst == D("9_000")


def test_gst_keyword_lookup(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("50_000"),
        description="management consulting",
        place_of_origin_state="Gujarat",
        place_of_supply_state="Gujarat",
    )
    resp = compute_gst(req)
    assert resp.gst_rate == D("0.18")
    assert resp.total_gst == D("9_000")


def test_gst_default_rate_when_no_info(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("10_000"),
        place_of_origin_state="Rajasthan",
        place_of_supply_state="Rajasthan",
    )
    resp = compute_gst(req)
    assert resp.gst_rate == D("0.18")
    assert resp.total_gst == D("1_800")


def test_gst_zero_taxable_value(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D(0),
        gst_rate=D("0.18"),
        place_of_origin_state="Kerala",
        place_of_supply_state="Kerala",
    )
    resp = compute_gst(req)
    assert resp.total_gst == D(0)
    assert resp.invoice_total == D(0)


def test_gst_exempt_hsn(gst_request_factory):
    req = gst_request_factory(
        taxable_value=D("10_000"),
        hsn_sac="0401",
        place_of_origin_state="Punjab",
        place_of_supply_state="Punjab",
    )
    resp = compute_gst(req)
    assert resp.gst_rate == D(0)
    assert resp.total_gst == D(0)
    assert resp.invoice_total == D("10_000")


def test_gst_missing_states_default_intra_state(gst_request_factory):
    req = gst_request_factory(taxable_value=D("10_000"), gst_rate=D("0.18"))
    resp = compute_gst(req)
    assert resp.is_inter_state is False
    assert resp.cgst + resp.sgst == resp.total_gst
