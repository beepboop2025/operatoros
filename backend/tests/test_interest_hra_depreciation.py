"""Unit tests for interest u/s 234, HRA exemption, and depreciation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.tax_engine import (
    compute_depreciation,
    compute_hra_exemption,
    compute_interest_234,
)


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


# --------------------------------------------------------------------------- #
#  Interest u/s 234A/B/C
# --------------------------------------------------------------------------- #
def test_interest_234_full_shortfall_no_payments(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("100_000"),
        due_date_of_filing=date(2026, 7, 31),
        actual_date_of_filing=date(2026, 10, 31),
    )
    resp = compute_interest_234(req)

    # 234A: 3 months delay (Aug/Sep/Oct)
    assert resp.interest_234a == D("3_000")
    # 234B: April 1 to actual filing date (Oct 31) = 7 months on shortfall of 100k
    assert resp.interest_234b == D("7_000")
    # 234C: q1 15k*3=450, q2 45k*3=1,350, q3 75k*3=2,250, q4 100k*1=1,000
    assert resp.interest_234c == D("5_050")
    assert resp.total_interest == D("15_050")
    # Late fee: tax after prepaid <= 5L → ₹1,000
    assert resp.late_fee_234f == D("1_000")


def test_interest_234a_one_day_delay(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("100_000"),
        due_date_of_filing=date(2026, 7, 31),
        actual_date_of_filing=date(2026, 8, 1),
    )
    resp = compute_interest_234(req)
    assert resp.interest_234a == D("1_000")


def test_interest_234a_no_delay(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("100_000"),
        due_date_of_filing=date(2026, 7, 31),
        actual_date_of_filing=date(2026, 7, 31),
    )
    resp = compute_interest_234(req)
    assert resp.interest_234a == D(0)
    assert resp.late_fee_234f == D(0)


def test_interest_234b_no_shortfall(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("100_000"),
        advance_tax_paid=D("90_000"),
        tds_paid=D("10_000"),
    )
    resp = compute_interest_234(req)
    # 90% threshold exactly met
    assert resp.interest_234b == D(0)


def test_interest_234c_total_below_threshold(interest_request_factory):
    req = interest_request_factory(total_tax_liability=D("9_999"))
    resp = compute_interest_234(req)
    assert resp.interest_234c == D(0)


def test_interest_234c_payments_on_time(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("100_000"),
        advance_tax_dates=[
            {"date": "2025-06-10", "amount": "15_000"},
            {"date": "2025-09-10", "amount": "30_000"},
            {"date": "2025-12-10", "amount": "30_000"},
            {"date": "2026-03-10", "amount": "25_000"},
        ],
    )
    resp = compute_interest_234(req)
    assert resp.interest_234c == D(0)


def test_interest_234_late_fee_above_5l(interest_request_factory):
    req = interest_request_factory(
        total_tax_liability=D("600_000"),
        due_date_of_filing=date(2026, 7, 31),
        actual_date_of_filing=date(2026, 8, 1),
    )
    resp = compute_interest_234(req)
    assert resp.late_fee_234f == D("5_000")


# --------------------------------------------------------------------------- #
#  HRA Exemption
# --------------------------------------------------------------------------- #
def test_hra_exemption_metro_full_exempt():
    result = compute_hra_exemption(
        basic_salary=D("600_000"),
        da=D(0),
        hra_received=D("120_000"),
        rent_paid=D("180_000"),
        is_metro=True,
    )
    # Limit 1: 120k, Limit 2: 50% salary = 300k, Limit 3: 180k - 10% salary = 120k
    assert result["exempt_amount"] == D("120_000")
    assert result["taxable_hra"] == D(0)


def test_hra_exemption_non_metro():
    result = compute_hra_exemption(
        basic_salary=D("600_000"),
        da=D(0),
        hra_received=D("120_000"),
        rent_paid=D("180_000"),
        is_metro=False,
    )
    # Limit 2: 40% salary = 240k
    assert result["exempt_amount"] == D("120_000")


def test_hra_exemption_rent_limit_binding():
    result = compute_hra_exemption(
        basic_salary=D("600_000"),
        da=D(0),
        hra_received=D("120_000"),
        rent_paid=D("100_000"),
        is_metro=True,
    )
    # Limit 3: 100k - 60k = 40k → binding
    assert result["exempt_amount"] == D("40_000")
    assert result["taxable_hra"] == D("80_000")


def test_hra_exemption_zero_rent():
    result = compute_hra_exemption(
        basic_salary=D("600_000"),
        da=D(0),
        hra_received=D("120_000"),
        rent_paid=D(0),
        is_metro=True,
    )
    assert result["exempt_amount"] == D(0)
    assert result["taxable_hra"] == D("120_000")


# --------------------------------------------------------------------------- #
#  Depreciation
# --------------------------------------------------------------------------- #
def test_depreciation_simple_wdv():
    schedule = compute_depreciation(
        asset_cost=D("100_000"),
        asset_type="plant_machinery_general",
        years=3,
    )
    assert len(schedule) == 3
    # Year 1: 15% of 100k = 15k, closing 85k
    assert schedule[0]["depreciation_amount"] == "15000.00"
    assert schedule[0]["closing_wdv"] == "85000.00"
    # Year 2: 15% of 85k = 12,750
    assert schedule[1]["depreciation_amount"] == "12750.00"
    assert schedule[1]["closing_wdv"] == "72250.00"
    # Year 3: 15% of 72,250 = 10,837.50
    assert schedule[2]["depreciation_amount"] == "10837.50"


def test_depreciation_additional_first_year():
    schedule = compute_depreciation(
        asset_cost=D("100_000"),
        asset_type="plant_machinery_general",
        years=2,
        additional_dep_eligible=True,
    )
    # Year 1: 15k normal + 20k additional = 35k
    assert schedule[0]["total_depreciation"] == "35000.00"
    assert schedule[0]["closing_wdv"] == "65000.00"
    # Year 2: 15% of 65k = 9,750 (no additional dep)
    assert schedule[1]["total_depreciation"] == "9750.00"


def test_depreciation_half_year_rule():
    schedule = compute_depreciation(
        asset_cost=D("100_000"),
        asset_type="plant_machinery_general",
        years=2,
        additional_dep_eligible=True,
        purchased_in_second_half=True,
    )
    # Year 1: 7.5% normal + 10% additional = 17.5k
    assert schedule[0]["depreciation_amount"] == "7500.00"
    assert schedule[0]["additional_depreciation"] == "10000.00"
    assert schedule[0]["total_depreciation"] == "17500.00"
    # Year 2: remaining 50% additional + full normal dep on opening WDV
    assert schedule[1]["additional_depreciation"] == "10000.00"
    assert schedule[1]["total_depreciation"] == "22375.00"  # 15% of 82.5k + 10k


def test_depreciation_zero_cost():
    schedule = compute_depreciation(
        asset_cost=D(0),
        asset_type="plant_machinery_general",
        years=3,
    )
    assert schedule[0]["depreciation_amount"] == "0.00"


def test_depreciation_unknown_asset_type():
    with pytest.raises(ValueError, match="Unknown asset_type"):
        compute_depreciation(asset_cost=D("100_000"), asset_type="unicorn")


def test_depreciation_runs_requested_years():
    schedule = compute_depreciation(
        asset_cost=D("1_000"),
        asset_type="plant_machinery_higher",  # 30%
        years=10,
    )
    # WDV with positive cost and rate < 1 never reaches zero, so all years run
    assert len(schedule) == 10
    assert Decimal(schedule[-1]["closing_wdv"]) > D(0)
