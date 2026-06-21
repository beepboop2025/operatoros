"""
Pure-logic unit tests for the statutory reference utilities.

These modules are dependency-free (stdlib only) and encode real Indian
tax/compliance rules, so they are the highest-value, fully-deterministic
surface to pin with assertions. No network, DB, Redis or API keys required.

Covers:
  * app.utils.cii_table          — Cost Inflation Index indexation
  * app.utils.compliance_calendar — statutory deadline generator
  * app.utils.gst_rates          — GST rate table + CGST/SGST/IGST split
  * app.utils.tds_rates          — TDS/TCS lookups + 206AA/206CC no-PAN rate
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.utils.cii_table import (
    CII_TABLE,
    CIINotFoundError,
    compute_indexed_cost,
    get_cii,
)
from app.utils.compliance_calendar import (
    _parse_fy,
    generate_compliance_calendar,
)
from app.utils.gst_rates import (
    GST_RATE_18,
    compute_gst_split,
    lookup_by_hsn,
    lookup_by_keyword,
    lookup_by_rate,
)
from app.utils.tds_rates import (
    compute_without_pan_rate,
    lookup_tds_by_payment_type,
    lookup_tds_section,
)


# ===========================================================================
#  CII TABLE  (Cost Inflation Index)
# ===========================================================================

class TestCII:
    def test_base_year_is_100(self):
        # By statute the base year 2001-02 is fixed at 100.
        assert get_cii("2001-02") == 100

    def test_known_value(self):
        assert get_cii("2023-24") == 348

    def test_monotonically_non_decreasing(self):
        # CII reflects inflation; it must never decrease year-on-year.
        years = sorted(CII_TABLE.keys())
        values = [CII_TABLE[y] for y in years]
        assert values == sorted(values)
        assert all(b > a for a, b in zip(values, values[1:]))  # strictly rising

    def test_missing_year_raises(self):
        with pytest.raises(CIINotFoundError) as exc:
            get_cii("1999-00")
        # The error must surface the offending FY and the available range.
        assert exc.value.fy == "1999-00"
        assert "2001-02" in str(exc.value)
        assert "2025-26" in str(exc.value)

    def test_indexed_cost_formula(self):
        # cost * (CII_sale / CII_purchase) = 100000 * 348/280
        result = compute_indexed_cost(Decimal("100000"), "2018-19", "2023-24")
        expected = (Decimal("100000") * Decimal("348") / Decimal("280")).quantize(
            Decimal("0.01")
        )
        assert result == expected
        assert result == Decimal("124285.71")

    def test_indexed_cost_same_year_is_identity(self):
        # Purchase FY == sale FY => ratio 1 => cost unchanged (to 2 dp).
        assert compute_indexed_cost(Decimal("55000"), "2020-21", "2020-21") == Decimal(
            "55000.00"
        )

    def test_indexed_cost_rounds_half_up(self):
        # 100 * 105/100 = 105.00 exactly; check 2-dp quantization is applied.
        out = compute_indexed_cost(Decimal("100"), "2001-02", "2002-03")
        assert out == Decimal("105.00")
        assert out.as_tuple().exponent == -2  # exactly two decimal places

    def test_indexed_cost_propagates_missing_year(self):
        with pytest.raises(CIINotFoundError):
            compute_indexed_cost(Decimal("1000"), "2000-01", "2023-24")


# ===========================================================================
#  COMPLIANCE CALENDAR
# ===========================================================================

class TestFYParsing:
    def test_short_form(self):
        assert _parse_fy("2025-26") == (2025, 2026)

    def test_within_century_rollover(self):
        # 2099-00 maps the 2-digit "00" onto the 2000 century of the start year.
        assert _parse_fy("2099-00") == (2099, 2000)

    def test_long_form(self):
        assert _parse_fy("2025-2026") == (2025, 2026)

    def test_typical_fy_end_is_start_plus_one(self):
        # For every realistic FY the end year is start + 1.
        for start in (2018, 2021, 2025):
            s, e = _parse_fy(f"{start}-{(start + 1) % 100:02d}")
            assert (s, e) == (start, start + 1)


class TestComplianceCalendar:
    def test_returns_sorted_by_due_date(self):
        cal = generate_compliance_calendar("private_limited", True, "2025-26")
        dates = [e["due_date"] for e in cal]
        assert dates == sorted(dates)

    def test_all_events_have_required_keys(self):
        cal = generate_compliance_calendar("individual", False, "2025-26")
        required = {"task_type", "description", "due_date", "form_name", "statute", "notes"}
        assert cal  # non-empty
        for e in cal:
            assert required <= set(e.keys())
            # due_date is ISO serialized
            date.fromisoformat(e["due_date"])

    def test_four_advance_tax_installments(self):
        cal = generate_compliance_calendar("individual", False, "2025-26")
        adv = [e for e in cal if e["task_type"] == "advance_tax"]
        assert len(adv) == 4
        # Statutory installment dates for FY 2025-26.
        due = sorted(e["due_date"] for e in adv)
        assert due == ["2025-06-15", "2025-09-15", "2025-12-15", "2026-03-15"]

    def test_individual_has_no_gst_returns(self):
        cal = generate_compliance_calendar("individual", False, "2025-26")
        assert not any(e["task_type"] == "gst_return" for e in cal)

    def test_company_has_gst_returns(self):
        cal = generate_compliance_calendar("private_limited", False, "2025-26")
        gst = [e for e in cal if e["task_type"] == "gst_return"]
        # 12 monthly GSTR-1 + 12 monthly GSTR-3B + 1 annual GSTR-9.
        assert len(gst) == 25
        assert any(e["form_name"] == "GSTR-9" for e in gst)

    def test_audit_changes_itr_due_date(self):
        # Non-audit individual files by 31 July; audit case by 31 October.
        non_audit = generate_compliance_calendar("individual", False, "2025-26")
        audited = generate_compliance_calendar("individual", True, "2025-26")

        def itr_main(cal):
            # The first itr_filing event (the original return, not belated).
            itrs = [e for e in cal if e["task_type"] == "itr_filing"]
            return min(itrs, key=lambda e: e["due_date"])["due_date"]

        assert itr_main(non_audit) == "2026-07-31"
        assert itr_main(audited) == "2026-10-31"

    def test_audit_adds_tax_audit_report(self):
        no = generate_compliance_calendar("partnership", False, "2025-26")
        yes = generate_compliance_calendar("partnership", True, "2025-26")
        assert not any(e["task_type"] == "tax_audit" for e in no)
        audit_events = [e for e in yes if e["task_type"] == "tax_audit"]
        assert any(e["form_name"].startswith("Form 3C") for e in audit_events)
        # Tax audit report deadline is 30 September.
        assert any(e["due_date"] == "2026-09-30" for e in audit_events)

    def test_company_gets_roc_filings_llp_does_not_get_company_forms(self):
        company = generate_compliance_calendar("private_limited", False, "2025-26")
        llp = generate_compliance_calendar("llp", False, "2025-26")

        company_roc = {e["form_name"] for e in company if e["task_type"] == "roc_filing"}
        assert {"AOC-4", "MGT-7", "ADT-1", "DPT-3", "MSME-1"} <= company_roc

        # LLP must NOT get company ROC forms, but must get LLP forms.
        llp_forms = {e["form_name"] for e in llp if e["task_type"] == "llp_form"}
        assert {"Form 11", "Form 8"} <= llp_forms
        assert not any(e["task_type"] == "roc_filing" for e in llp)

    def test_dir3_kyc_for_company_and_llp_only(self):
        for et in ("private_limited", "public_limited", "llp"):
            cal = generate_compliance_calendar(et, False, "2025-26")
            assert any(e["task_type"] == "dir3_kyc" for e in cal), et
        for et in ("individual", "huf", "partnership"):
            cal = generate_compliance_calendar(et, False, "2025-26")
            assert not any(e["task_type"] == "dir3_kyc" for e in cal), et

    def test_tds_returns_are_quarterly_plus_certificates(self):
        cal = generate_compliance_calendar("private_limited", False, "2025-26")
        tds = [e for e in cal if e["task_type"] == "tds_return"]
        # 4 quarterly returns + Form 16 + Form 16A.
        assert len(tds) == 6
        forms = {e["form_name"] for e in tds}
        assert "Form 16" in forms and "Form 16A" in forms


# ===========================================================================
#  GST RATES
# ===========================================================================

class TestGSTLookups:
    def test_lookup_by_hsn_known_code(self):
        results = lookup_by_hsn("998311")
        assert results
        assert all(r.hsn_sac == "998311" for r in results)
        assert results[0].rate == GST_RATE_18

    def test_lookup_by_hsn_unknown_returns_empty(self):
        assert lookup_by_hsn("000000") == []

    def test_lookup_by_keyword_is_case_insensitive(self):
        lower = lookup_by_keyword("restaurant")
        upper = lookup_by_keyword("RESTAURANT")
        assert lower == upper
        assert lower  # at least one restaurant entry exists

    def test_lookup_by_rate(self):
        eighteen = lookup_by_rate(GST_RATE_18)
        assert eighteen
        assert all(e.rate == GST_RATE_18 for e in eighteen)


class TestGSTSplit:
    def test_intra_state_splits_evenly(self):
        out = compute_gst_split(Decimal("10000"), Decimal("0.18"), is_inter_state=False)
        assert out["cgst"] == Decimal("900.00")
        assert out["sgst"] == Decimal("900.00")
        assert out["igst"] == Decimal("0")
        assert out["total_gst"] == Decimal("1800.00")
        assert out["invoice_total"] == Decimal("11800.00")

    def test_inter_state_uses_igst_only(self):
        out = compute_gst_split(Decimal("10000"), Decimal("0.18"), is_inter_state=True)
        assert out["igst"] == Decimal("1800.00")
        assert out["cgst"] == Decimal("0")
        assert out["sgst"] == Decimal("0")
        assert out["total_gst"] == Decimal("1800.00")

    def test_cgst_plus_sgst_equals_total_even_with_rounding(self):
        # Odd taxable value forces a rounding situation; the function must keep
        # CGST + SGST == total_gst (it derives sgst as total - cgst).
        out = compute_gst_split(Decimal("999.99"), Decimal("0.05"), is_inter_state=False)
        assert out["cgst"] + out["sgst"] == out["total_gst"]
        assert out["invoice_total"] == out["taxable_value"] + out["total_gst"]

    def test_zero_rate(self):
        out = compute_gst_split(Decimal("5000"), Decimal("0.00"), is_inter_state=False)
        assert out["total_gst"] == Decimal("0.00")
        assert out["invoice_total"] == Decimal("5000")


# ===========================================================================
#  TDS / TCS RATES
# ===========================================================================

class TestTDSLookups:
    def test_lookup_section_194a(self):
        entries = lookup_tds_section("194A")
        assert entries
        assert all(e.section == "194A" for e in entries)
        assert entries[0].rate_with_pan == Decimal("0.10")
        assert entries[0].threshold == Decimal("40000")

    def test_lookup_section_unknown_empty(self):
        assert lookup_tds_section("999Z") == []

    def test_lookup_by_payment_type_keyword(self):
        salary = lookup_tds_by_payment_type("salary")
        assert any(e.section == "192" for e in salary)


class TestNoPanRate:
    def test_slab_based_tds_defaults_to_20pct(self):
        # rate_with_pan None => 206AA flat 20%.
        assert compute_without_pan_rate(None) == Decimal("0.20")

    def test_206AA_takes_higher_of_double_or_20pct(self):
        # 1% contractor rate doubled = 2% < 20% floor => 20%.
        assert compute_without_pan_rate(Decimal("0.01")) == Decimal("0.20")
        # 30% lottery rate doubled = 60% > 20% floor => 60%.
        assert compute_without_pan_rate(Decimal("0.30")) == Decimal("0.60")
        # 10% interest doubled = 20% == floor => 20%.
        assert compute_without_pan_rate(Decimal("0.10")) == Decimal("0.20")

    def test_206CC_tcs_floor_is_5pct(self):
        # TCS: higher of 5% or twice the rate.
        assert compute_without_pan_rate(Decimal("0.01"), is_tcs=True) == Decimal("0.05")
        assert compute_without_pan_rate(Decimal("0.05"), is_tcs=True) == Decimal("0.10")
