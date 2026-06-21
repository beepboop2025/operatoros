"""Unit tests for Phase 7 NRI cross-border taxation engines."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.nri_engine import (
    CrossBorderGSTRequest,
    CrossBorderTransactionType,
    CustomsTariffRequest,
    DTAARequest,
    FTCCreditCountryInput,
    FTCRequest,
    ResidentialStatusRequest,
    Section195PaymentType,
    Section195Request,
    compute_cross_border_gst,
    compute_customs_tariff,
    compute_ftc,
    compute_section_195,
    determine_residential_status,
    explore_dtaa,
)


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


# --------------------------------------------------------------------------- #
#  Residential status
# --------------------------------------------------------------------------- #


class TestResidentialStatus:
    def test_nri_below_60_day_threshold(self):
        req = ResidentialStatusRequest(
            assessment_year="2025-26",
            days_in_india_current_fy=50,
            days_in_india_prior_4_fys=[20, 30, 10, 5],
            is_indian_citizen=False,
            indian_source_income=D("1_000_000"),
        )
        resp = determine_residential_status(req)
        assert resp.status.value == "NRI"
        assert resp.taxable_scope.value == "india_sourced"
        assert resp.threshold_days == 60

    def test_resident_182_days(self):
        req = ResidentialStatusRequest(
            assessment_year="2025-26",
            days_in_india_current_fy=200,
            days_in_india_prior_4_fys=[0, 0, 0, 0],
        )
        resp = determine_residential_status(req)
        assert resp.status.value == "Resident"
        assert resp.taxable_scope.value == "global"

    def test_rnor_via_9_out_of_10(self):
        req = ResidentialStatusRequest(
            assessment_year="2025-26",
            days_in_india_current_fy=200,
            days_in_india_prior_4_fys=[100, 100, 100, 100],
            prior_10_fys_resident=[False] * 9 + [True],
        )
        resp = determine_residential_status(req)
        assert resp.status.value == "RNOR"
        assert resp.taxable_scope.value == "india_sourced_plus_foreign_controlled"

    def test_deemed_resident_citizen_high_income_not_resident_elsewhere(self):
        req = ResidentialStatusRequest(
            assessment_year="2025-26",
            days_in_india_current_fy=100,
            days_in_india_prior_4_fys=[0, 0, 0, 0],
            is_indian_citizen=True,
            indian_source_income=D("2_000_000"),
            tax_resident_elsewhere=False,
        )
        resp = determine_residential_status(req)
        assert resp.status.value == "Deemed Resident"
        assert resp.is_deemed_resident is True
        assert resp.taxable_scope.value == "global"

    def test_visitor_high_income_threshold_pre_2026(self):
        # Tax-resident elsewhere so deemed-resident rule does not apply.
        req = ResidentialStatusRequest(
            assessment_year="2025-26",
            days_in_india_current_fy=150,
            days_in_india_prior_4_fys=[365, 0, 0, 0],
            is_indian_citizen=True,
            indian_source_income=D("2_000_000"),
            tax_resident_elsewhere=True,
        )
        resp = determine_residential_status(req)
        # 150 < 182 => NRI in pre-Apr-2026 rule
        assert resp.status.value == "NRI"
        assert resp.threshold_days == 182

    def test_visitor_high_income_threshold_post_2026(self):
        # Tax-resident elsewhere so deemed-resident rule does not apply.
        req = ResidentialStatusRequest(
            assessment_year="2026-27",
            days_in_india_current_fy=150,
            days_in_india_prior_4_fys=[365, 0, 0, 0],
            is_indian_citizen=True,
            indian_source_income=D("2_000_000"),
            tax_resident_elsewhere=True,
        )
        resp = determine_residential_status(req)
        # 150 >= 120 => resident in post-Apr-2026 rule
        assert resp.status.value == "Resident"
        assert resp.threshold_days == 120

    def test_employment_exception_uses_182_days(self):
        req = ResidentialStatusRequest(
            assessment_year="2026-27",
            days_in_india_current_fy=150,
            days_in_india_prior_4_fys=[400, 0, 0, 0],
            is_indian_citizen=True,
            leaving_for_employment=True,
        )
        resp = determine_residential_status(req)
        # threshold 182 => not resident under second condition
        assert resp.status.value == "NRI"
        assert resp.threshold_days == 182


# --------------------------------------------------------------------------- #
#  DTAA explorer
# --------------------------------------------------------------------------- #


class TestDTAAExplorer:
    def test_top_corridor_usa(self):
        req = DTAARequest(country="USA")
        resp = explore_dtaa(req)
        assert resp.country == "United States of America"
        assert resp.country_code == "US"
        assert resp.trc_required is True
        assert resp.form_10f_required is True
        assert resp.ca_review_required is True
        income_types = {r["income_type"] for r in resp.rates}
        assert income_types == {
            "dividends",
            "interest",
            "royalty",
            "fees_for_technical_services",
            "capital_gains",
        }

    def test_unknown_country(self):
        req = DTAARequest(country="Germany")
        resp = explore_dtaa(req)
        assert resp.country == "Germany"
        assert resp.country_code == ""
        assert resp.ca_review_required is True
        assert "not yet in the top-corridor" in resp.notes


# --------------------------------------------------------------------------- #
#  Section 195
# --------------------------------------------------------------------------- #


class TestSection195:
    def test_non_nri_not_applicable(self):
        req = Section195Request(
            payment_type=Section195PaymentType.interest,
            payment_amount=D("100_000"),
            payee_is_nri=False,
        )
        resp = compute_section_195(req)
        assert resp.applicable_regime == "not_applicable"
        assert resp.form_15ca_required is False

    def test_domestic_rate_without_trc(self):
        req = Section195Request(
            payment_type=Section195PaymentType.interest,
            payment_amount=D("100_000"),
            payee_is_nri=True,
            domestic_rate_override=D("0.20"),
            treaty_rate_override=D("0.10"),
            payee_has_trc=False,
        )
        resp = compute_section_195(req)
        assert resp.applicable_rate == D("0.20")
        assert resp.tds_amount == D("20_000")
        assert resp.applicable_regime == "Finance Act"

    def test_treaty_rate_with_trc(self):
        req = Section195Request(
            payment_type=Section195PaymentType.interest,
            payment_amount=D("100_000"),
            payee_is_nri=True,
            domestic_rate_override=D("0.20"),
            treaty_rate_override=D("0.10"),
            payee_has_trc=True,
        )
        resp = compute_section_195(req)
        assert resp.applicable_rate == D("0.10")
        assert resp.tds_amount == D("10_000")
        assert resp.applicable_regime == "DTAA (lower of domestic / treaty)"

    def test_form_15cb_threshold(self):
        req = Section195Request(
            payment_type=Section195PaymentType.royalty,
            payment_amount=D("600_000"),
            payee_is_nri=True,
            domestic_rate_override=D("0.10"),
        )
        resp = compute_section_195(req)
        assert resp.form_15ca_required is True
        assert resp.form_15cb_required is True
        assert resp.tds_amount == D("60_000")

    def test_form_15e_certificate(self):
        req = Section195Request(
            payment_type=Section195PaymentType.property_sale,
            payment_amount=D("5_000_000"),
            property_sale_consideration=D("5_000_000"),
            payee_is_nri=True,
            has_form_15e_certificate=True,
            certificate_rate=D("0.05"),
        )
        resp = compute_section_195(req)
        assert resp.form_15e_applied is True
        assert resp.applicable_rate == D("0.05")
        assert resp.tds_amount == D("250_000")


# --------------------------------------------------------------------------- #
#  Foreign Tax Credit
# --------------------------------------------------------------------------- #


class TestFTC:
    def test_ftc_capped_at_indian_tax_attributable(self):
        req = FTCRequest(
            assessment_year="2025-26",
            total_income=D("1_000_000"),
            total_indian_tax=D("100_000"),
            countries=[
                FTCCreditCountryInput(
                    country="USA",
                    foreign_income=D("200_000"),
                    foreign_tax_paid=D("50_000"),
                    has_dtaa=True,
                )
            ],
        )
        resp = compute_ftc(req)
        assert resp.average_indian_tax_rate == D("0.10")
        country = resp.per_country[0]
        assert country.indian_tax_on_foreign_income == D("20_000")
        assert country.allowable_credit == D("20_000")
        assert country.disallowance == D("30_000")
        assert country.method == "DTAA"
        assert resp.total_allowable_credit == D("20_000")

    def test_ftc_filed_on_time(self):
        req = FTCRequest(
            assessment_year="2026-27",
            total_income=D("1_000_000"),
            total_indian_tax=D("100_000"),
            countries=[
                FTCCreditCountryInput(
                    country="UAE",
                    foreign_income=D("100_000"),
                    foreign_tax_paid=D("5_000"),
                )
            ],
            filing_date=date(2026, 7, 31),
        )
        resp = compute_ftc(req)
        assert resp.form_67_due_date == date(2026, 7, 31)
        assert resp.is_filed_on_time is True

    def test_ftc_late_filing(self):
        req = FTCRequest(
            assessment_year="2025-26",
            total_income=D("1_000_000"),
            total_indian_tax=D("100_000"),
            countries=[
                FTCCreditCountryInput(
                    country="UK",
                    foreign_income=D("100_000"),
                    foreign_tax_paid=D("5_000"),
                )
            ],
            filing_date=date(2025, 8, 5),
        )
        resp = compute_ftc(req)
        assert resp.is_filed_on_time is False


# --------------------------------------------------------------------------- #
#  Customs & Tariffs
# --------------------------------------------------------------------------- #


class TestCustomsTariff:
    def test_missing_rates_return_none_totals(self):
        req = CustomsTariffRequest(
            hsn_code="8517",
            cif_value=D("100_000"),
        )
        resp = compute_customs_tariff(req)
        assert resp.import_duty_total is None
        assert resp.total_landed_cost is None
        assert "bcd" in resp.missing_rates
        assert "igst" in resp.missing_rates

    def test_full_computation_with_overrides(self):
        req = CustomsTariffRequest(
            hsn_code="8517",
            cif_value=D("100_000"),
            bcd_rate_override=D("0.20"),
            sws_rate_override=D("0.10"),
            cess_rate_override=D("0.05"),
            igst_rate_override=D("0.18"),
            fta_code="INDIA_UAE_CEPA",
        )
        resp = compute_customs_tariff(req)
        assert resp.bcd_amount == D("20_000")
        assert resp.sws_amount == D("2_000")
        assert resp.cess_amount == D("6_100")
        assert resp.igst_amount == D("23_058")
        assert resp.import_duty_total == D("51_158")
        assert resp.total_landed_cost == D("151_158")
        assert resp.fta_applied is True


# --------------------------------------------------------------------------- #
#  GST cross-border
# --------------------------------------------------------------------------- #


class TestCrossBorderGST:
    def test_export_with_lut_zero_rated(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.export,
            has_lut=True,
            recipient_country="USA",
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.export_zero_rated is True
        assert resp.total_gst == D("0")
        assert resp.invoice_total == D("100_000")

    def test_export_without_lut_charges_igst(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.export,
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.export_zero_rated is False
        assert resp.igst == D("18_000")
        assert resp.invoice_total == D("118_000")

    def test_import_igst_includes_duty(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.import_,
            import_duty_amount=D("20_000"),
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.igst == D("21_600")
        assert resp.invoice_total == D("141_600")

    def test_oidar_b2b_reverse_charge(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.oidar,
            is_b2b=True,
            recipient_country="Germany",
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.reverse_charge is True
        assert resp.total_gst == D("18_000")
        # B2B invoice does not add tax to invoice_total (recipient pays)
        assert resp.invoice_total == D("100_000")

    def test_oidar_b2c_supplier_charge(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.oidar,
            is_b2b=False,
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.reverse_charge is False
        assert resp.invoice_total == D("118_000")

    def test_domestic_cross_border_service(self):
        req = CrossBorderGSTRequest(
            taxable_value=D("100_000"),
            transaction_type=CrossBorderTransactionType.domestic,
            supply_type="services",
            place_of_supply="Maharashtra",
            gst_rate=D("0.18"),
        )
        resp = compute_cross_border_gst(req)
        assert resp.total_gst == D("18_000")
        assert resp.place_of_supply == "Maharashtra"


class TestDemoDataAndSourcedRates:
    """Phase: sourced indicative DTAA rates + customs demo-mode sample rates."""

    def test_dtaa_returns_sourced_indicative_rates(self) -> None:
        # DTAA now returns real headline rates, still flagged for CA verification.
        resp = explore_dtaa(DTAARequest(country="USA", income_type="dividends"))
        assert resp.rates[0]["rate_percent"] == 15.0
        assert resp.ca_review_required is True
        assert "Indicative" in resp.source_citation

    def test_customs_without_demo_stays_honest(self) -> None:
        # Default (no demo): unsourced HSN reports missing rates, never guesses.
        resp = compute_customs_tariff(
            CustomsTariffRequest(hsn_code="8517", cif_value=Decimal("100000"))
        )
        assert resp.is_sample_data is False
        assert "bcd" in resp.missing_rates
        assert resp.total_landed_cost is None

    def test_customs_demo_uses_labeled_sample_rates(self) -> None:
        # Demo mode: fills illustrative rates, computes, and flags as sample.
        resp = compute_customs_tariff(
            CustomsTariffRequest(hsn_code="8517", cif_value=Decimal("100000"), demo=True)
        )
        assert resp.is_sample_data is True
        assert resp.total_landed_cost is not None
        assert "SAMPLE DATA" in resp.notes

    def test_customs_demo_unknown_hsn_still_honest(self) -> None:
        # Demo mode but no sample for this HSN -> still reports missing, not faked.
        resp = compute_customs_tariff(
            CustomsTariffRequest(hsn_code="9999", cif_value=Decimal("100000"), demo=True)
        )
        assert resp.is_sample_data is False
        assert resp.missing_rates
