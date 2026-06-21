"""Unit tests for income-tax computation helpers and the public API."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.tax_engine import (
    AgeCategory,
    NEW_REGIME_SLABS,
    OLD_REGIME_SLABS,
    _apply_marginal_relief,
    _compute_old_regime_deductions,
    _compute_tax_from_slabs,
    compute_income_tax,
)
from app.utils.tax_constants import (
    CESS_RATE,
    REBATE_87A_OLD_LIMIT,
    REBATE_87A_OLD_MAX,
    STANDARD_DEDUCTION_NEW_REGIME,
    STANDARD_DEDUCTION_OLD_REGIME,
)


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


# --------------------------------------------------------------------------- #
#  _compute_tax_from_slabs
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "income,slabs,expected_tax",
    [
        (D(0), OLD_REGIME_SLABS["below_60"], D(0)),
        (D(250_000), OLD_REGIME_SLABS["below_60"], D(0)),
        (D(300_000), OLD_REGIME_SLABS["below_60"], D(2_500)),
        (D(500_000), OLD_REGIME_SLABS["below_60"], D(12_500)),
        (D(700_000), OLD_REGIME_SLABS["below_60"], D(52_500)),
        (D(1_000_000), OLD_REGIME_SLABS["below_60"], D(112_500)),
        (D(1_500_000), OLD_REGIME_SLABS["below_60"], D(262_500)),
        # Senior citizen slabs
        (D(300_000), OLD_REGIME_SLABS["60_to_80"], D(0)),
        (D(500_000), OLD_REGIME_SLABS["60_to_80"], D(10_000)),
        # Super senior slabs
        (D(500_000), OLD_REGIME_SLABS["80_plus"], D(0)),
        (D(1_000_000), OLD_REGIME_SLABS["80_plus"], D(100_000)),
        # New regime AY 2025-26
        (D(300_000), NEW_REGIME_SLABS["2025-26"], D(0)),
        (D(700_000), NEW_REGIME_SLABS["2025-26"], D(20_000)),
        (D(1_000_000), NEW_REGIME_SLABS["2025-26"], D(50_000)),
        (D(1_500_000), NEW_REGIME_SLABS["2025-26"], D(140_000)),
        # New regime AY 2026-27
        (D(400_000), NEW_REGIME_SLABS["2026-27"], D(0)),
        (D(800_000), NEW_REGIME_SLABS["2026-27"], D(20_000)),
        (D(1_200_000), NEW_REGIME_SLABS["2026-27"], D(60_000)),
        (D(2_500_000), NEW_REGIME_SLABS["2026-27"], D(330_000)),
    ],
)
def test_compute_tax_from_slabs(income, slabs, expected_tax):
    tax, working = _compute_tax_from_slabs(income, slabs)
    assert tax == expected_tax
    assert isinstance(working, list)
    # Sum of working steps must equal the tax
    assert sum(D(step["tax"].replace("₹", "").replace(",", "")) for step in working) == tax


def test_compute_tax_from_slabs_negative_income():
    tax, working = _compute_tax_from_slabs(D(-10_000), OLD_REGIME_SLABS["below_60"])
    assert tax == D(0)
    assert working == []


def test_compute_tax_from_slabs_very_high_income():
    income = D("50000000")
    tax, _ = _compute_tax_from_slabs(income, OLD_REGIME_SLABS["below_60"])
    # 0-250k:0, 250-500k:12.5k, 500k-1M:100k, 1M-50M:30% of 49M = 14.7M
    expected = D("12_500") + D("100_000") + (D("49_000_000") * D("0.30"))
    assert tax == expected


# --------------------------------------------------------------------------- #
#  _apply_marginal_relief
# --------------------------------------------------------------------------- #
def test_marginal_relief_no_surcharge():
    adjusted, relief, applied = _apply_marginal_relief(
        income=D("4_900_000"),
        tax_before_surcharge=D("1_237_500"),
        surcharge=D(0),
        surcharge_threshold=D("5_000_000"),
        slabs=OLD_REGIME_SLABS["below_60"],
    )
    assert adjusted == D(0)
    assert relief == D(0)
    assert applied is False


def test_marginal_relief_income_at_threshold():
    adjusted, relief, applied = _apply_marginal_relief(
        income=D("5_000_000"),
        tax_before_surcharge=D("1_312_500"),
        surcharge=D("131_250"),
        surcharge_threshold=D("5_000_000"),
        slabs=OLD_REGIME_SLABS["below_60"],
    )
    assert adjusted == D("131_250")
    assert relief == D(0)
    assert applied is False


def test_marginal_relief_just_above_threshold():
    """Income ₹10 above the threshold — surcharge should collapse to a few rupees."""
    income = D("5_000_010")
    tax_before = D("1_312_503")
    surcharge = D("131_250.30")
    adjusted, relief, applied = _apply_marginal_relief(
        income=income,
        tax_before_surcharge=tax_before,
        surcharge=surcharge,
        surcharge_threshold=D("5_000_000"),
        slabs=OLD_REGIME_SLABS["below_60"],
    )
    assert applied is True
    assert relief == D("131_243.30")
    assert adjusted == D("7.00")


def test_marginal_relief_wipes_surcharge():
    """A ₹1 lakh excess should not pay more than threshold tax + excess."""
    income = D("5_100_000")
    tax_before = D("2_527_500")
    surcharge = D("252_750")
    adjusted, relief, applied = _apply_marginal_relief(
        income=income,
        tax_before_surcharge=tax_before,
        surcharge=surcharge,
        surcharge_threshold=D("5_000_000"),
        slabs=OLD_REGIME_SLABS["below_60"],
    )
    assert applied is True
    assert relief == D("1_367_750")
    assert adjusted == D(0)


# --------------------------------------------------------------------------- #
#  _compute_old_regime_deductions
# --------------------------------------------------------------------------- #
def test_old_regime_deductions_capping(deductions_factory):
    d = deductions_factory(
        sec_80c=D("180_000"),
        sec_80ccc=D("30_000"),
        sec_80ccd_1=D("20_000"),
        sec_80ccd_1b=D("60_000"),
        sec_80d_self=D("30_000"),
        sec_80d_parents=D("60_000"),
        sec_80gg=D("80_000"),
    )
    total, details = _compute_old_regime_deductions(d, AgeCategory.below_60)
    # 80C group capped at 150k, 80CCD(1B) capped at 50k, 80D self capped at 25k,
    # parents capped at 50k (code uses senior limit), 80GG capped at 60k.
    assert details["80C/80CCC/80CCD(1)"] == D("150_000")
    assert details["80CCD(1B)"] == D("50_000")
    assert details["80D (self)"] == D("25_000")
    assert details["80D (parents)"] == D("50_000")
    assert details["80GG"] == D("60_000")
    expected_total = D("150_000") + D("50_000") + D("25_000") + D("50_000") + D("60_000")
    assert total == expected_total


def test_old_regime_deductions_senior_ttb(deductions_factory):
    d = deductions_factory(sec_80tta=D("12_000"), sec_80ttb=D("60_000"))
    total, details = _compute_old_regime_deductions(d, AgeCategory.senior_60_to_80)
    # Senior: 80TTA ignored, 80TTB capped at 50k
    assert "80TTA" not in details
    assert details["80TTB"] == D("50_000")
    assert total == D("50_000")


def test_old_regime_deductions_non_senior_tta(deductions_factory):
    d = deductions_factory(sec_80tta=D("12_000"), sec_80ttb=D("60_000"))
    total, details = _compute_old_regime_deductions(d, AgeCategory.below_60)
    # Non-senior: 80TTA capped at 10k, 80TTB ignored
    assert details["80TTA"] == D("10_000")
    assert "80TTB" not in details
    assert total == D("10_000")


def test_old_regime_80ccd2_allowed(deductions_factory):
    d = deductions_factory(sec_80ccd_2=D("75_000"))
    total, details = _compute_old_regime_deductions(d, AgeCategory.below_60)
    assert details["80CCD(2)"] == D("75_000")
    assert total == D("75_000")


# --------------------------------------------------------------------------- #
#  compute_income_tax — full integration
# --------------------------------------------------------------------------- #
def test_compute_income_tax_salary_one_million_no_deductions(income_request_factory):
    req = income_request_factory(gross_salary=D("1_000_000"))
    resp = compute_income_tax(req)

    # Old regime
    old = resp.old_regime
    std_old = min(STANDARD_DEDUCTION_OLD_REGIME, D("1_000_000"))
    assert old.standard_deduction == std_old
    assert old.total_income == D("950_000")
    expected_old_normal = D("102_500")  # 12.5k + 90k
    assert old.tax_on_normal_income == expected_old_normal
    assert old.rebate_87a == D(0)
    assert old.tax_after_rebate == expected_old_normal
    assert old.surcharge == D(0)
    expected_old_cess = (expected_old_normal * CESS_RATE).quantize(D("0.01"))
    assert old.cess == expected_old_cess
    assert old.total_tax_liability == (expected_old_normal + expected_old_cess).quantize(D("0.01"))

    # New regime AY 2025-26
    new = resp.new_regime
    std_new = min(STANDARD_DEDUCTION_NEW_REGIME, D("1_000_000"))
    assert new.standard_deduction == std_new
    assert new.total_income == D("925_000")
    expected_new_normal = D("42_500")  # 20k + 22.5k
    assert new.tax_on_normal_income == expected_new_normal
    assert new.rebate_87a == D(0)
    assert new.total_tax_liability == (expected_new_normal * (D(1) + CESS_RATE)).quantize(D("0.01"))

    assert resp.recommended_regime == "new"
    assert resp.tax_saving == old.total_tax_liability - new.total_tax_liability


def test_compute_income_tax_full_rebate_old_and_new(income_request_factory):
    req = income_request_factory(gross_salary=D("500_000"))
    resp = compute_income_tax(req)

    assert resp.old_regime.total_income == D("450_000")
    assert resp.old_regime.tax_on_normal_income == D("10_000")
    assert resp.old_regime.rebate_87a == D("10_000")
    assert resp.old_regime.total_tax_liability == D(0)

    assert resp.new_regime.total_income == D("425_000")
    assert resp.new_regime.tax_on_normal_income == D("6_250")
    assert resp.new_regime.rebate_87a == D("6_250")
    assert resp.new_regime.total_tax_liability == D(0)


def test_compute_income_tax_old_regime_better(income_request_factory, deductions_factory):
    req = income_request_factory(
        gross_salary=D("1_500_000"),
        deductions=deductions_factory(
            sec_80c=D("150_000"),
            sec_80d_self=D("25_000"),
            sec_80ccd_1b=D("50_000"),
            sec_80ccd_2=D("75_000"),
            sec_80e=D("200_000"),
            sec_80u=D("125_000"),
        ),
    )
    resp = compute_income_tax(req)

    # Chapter VI-A = 150k + 50k + 75k + 25k + 200k + 125k = 625k
    old = resp.old_regime
    assert old.chapter_via_deductions == D("625_000")
    assert old.total_income == D("825_000")
    assert old.tax_on_normal_income == D("77_500")
    assert resp.recommended_regime == "old"

    new = resp.new_regime
    assert new.chapter_via_deductions == D("75_000")  # only 80CCD(2)
    assert new.total_income == D("1_350_000")
    assert new.tax_on_normal_income == D("110_000")


def test_compute_income_tax_new_regime_ay2026_rebate(income_request_factory):
    req = income_request_factory(
        assessment_year="2026-27",
        gross_salary=D("1_000_000"),
    )
    resp = compute_income_tax(req)
    new = resp.new_regime
    assert new.total_income == D("925_000")
    expected_tax = D("32_500")  # AY2026 slabs
    assert new.tax_on_normal_income == expected_tax
    assert new.rebate_87a == expected_tax
    assert new.total_tax_liability == D(0)


def test_compute_income_tax_surcharge_old_regime(income_request_factory):
    req = income_request_factory(gross_salary=D("6_000_000"))
    resp = compute_income_tax(req)
    old = resp.old_regime
    assert old.total_income == D("5_950_000")
    assert old.surcharge_rate == D("0.10")
    assert old.surcharge == D("159_750")
    assert old.marginal_relief_applied is False
    assert old.total_tax_liability == D("1_827_540")


def test_compute_income_tax_marginal_relief_old_regime(income_request_factory):
    """Marginal relief should cap the surcharge just above ₹5 lakh."""
    req = income_request_factory(gross_salary=D("5_100_000"))
    resp = compute_income_tax(req)
    old = resp.old_regime
    assert old.total_income == D("5_050_000")
    assert old.surcharge_rate == D("0.10")
    assert old.marginal_relief_applied is True
    assert old.marginal_relief_amount == D("97_750")
    assert old.surcharge == D("35_000")
    expected_tax_after_rebate = D("1_327_500")
    expected_total_tax = expected_tax_after_rebate + old.surcharge
    expected_cess = (expected_total_tax * CESS_RATE).quantize(D("0.01"))
    assert old.total_tax_liability == (expected_total_tax + expected_cess).quantize(D("0.01"))


def test_compute_income_tax_negative_income_clamped(income_request_factory):
    req = income_request_factory(
        gross_salary=D("300_000"),
        income_from_house_property=D("-500_000"),
    )
    resp = compute_income_tax(req)
    assert resp.old_regime.total_income == D(0)
    assert resp.new_regime.total_income == D(0)


def test_compute_income_tax_special_rate_income(income_request_factory):
    req = income_request_factory(
        gross_salary=D("1_000_000"),
        short_term_capital_gains_equity=D("200_000"),
        long_term_capital_gains=D("300_000"),
    )
    resp = compute_income_tax(req)
    new = resp.new_regime
    assert new.tax_on_stcg_equity == D("40_000")  # 20% of 200k
    assert new.tax_on_ltcg == D("21_875")  # 12.5% of (300k-125k)
    assert new.gross_total_income == D("1_500_000")


def test_compute_income_tax_taxes_paid(income_request_factory):
    req = income_request_factory(
        gross_salary=D("1_000_000"),
        tds_already_paid=D("20_000"),
        advance_tax_paid=D("15_000"),
    )
    resp = compute_income_tax(req)
    assert resp.new_regime.taxes_paid == D("35_000")
    assert resp.new_regime.net_tax_payable == resp.new_regime.total_tax_liability - D("35_000")


# --------------------------------------------------------------------------- #
#  Regime boundary / edge cases
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("gross", [D(0), D(1), D(49_999), D(50_000)])
def test_standard_deduction_old_capped_at_salary(income_request_factory, gross):
    req = income_request_factory(gross_salary=gross)
    resp = compute_income_tax(req)
    assert resp.old_regime.standard_deduction == min(gross, STANDARD_DEDUCTION_OLD_REGIME)


def test_compute_income_tax_zero_input(income_request_factory):
    req = income_request_factory()
    resp = compute_income_tax(req)
    assert resp.old_regime.total_tax_liability == D(0)
    assert resp.new_regime.total_tax_liability == D(0)
    assert resp.recommended_regime == "old"  # tie → old
    assert resp.tax_saving == D(0)
