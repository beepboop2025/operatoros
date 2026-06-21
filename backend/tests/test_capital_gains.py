"""Unit tests for capital-gains computation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.tax_engine import AssetType, CapitalGainsRequest, compute_capital_gains


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def test_listed_equity_ltcg_with_exemption():
    req = CapitalGainsRequest(
        asset_type=AssetType.listed_equity,
        purchase_date=date(2022, 1, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("700_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is True
    assert resp.classification == "LTCG"
    assert resp.capital_gain == D("200_000")
    assert resp.exemption_available == D("125_000")
    assert resp.taxable_gain == D("75_000")
    assert resp.tax_rate == D("0.125")
    assert resp.tax_amount == D("9_375")


def test_listed_equity_stcg():
    req = CapitalGainsRequest(
        asset_type=AssetType.listed_equity,
        purchase_date=date(2024, 1, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("600_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is False
    assert resp.classification == "STCG"
    assert resp.tax_rate == D("0.20")
    assert resp.taxable_gain == D("100_000")
    assert resp.tax_amount == D("20_000")


def test_listed_equity_ltcg_below_exemption():
    req = CapitalGainsRequest(
        asset_type=AssetType.equity_mutual_fund,
        purchase_date=date(2023, 1, 1),
        sale_date=date(2025, 1, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("600_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.taxable_gain == D(0)
    assert resp.tax_amount == D(0)


def test_immovable_property_pre_july_2024_with_indexation():
    """Grandfathered property should recommend indexation when it saves tax."""
    req = CapitalGainsRequest(
        asset_type=AssetType.immovable_property,
        purchase_date=date(2018, 4, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("1_000_000"),
        improvement_cost=D("200_000"),
        sale_consideration=D("2_000_000"),
        expenses_on_transfer=D("50_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is True
    assert resp.recommended_option == "with_indexation"

    # CII: purchase FY 2018-19 = 280, sale FY 2024-25 = 363
    indexed_cost = (D("1_000_000") * D(363) / D(280)).quantize(D("0.01"))
    indexed_improvement = (D("200_000") * D(363) / D(280)).quantize(D("0.01"))
    net_sale = D("2_000_000") - D("50_000")
    gain_with_idx = net_sale - indexed_cost - indexed_improvement
    expected_tax_with_idx = (gain_with_idx * D("0.20")).quantize(D("0.01"))

    assert resp.option_with_indexation is not None
    assert resp.option_with_indexation["indexed_cost"] == indexed_cost
    assert resp.option_with_indexation["tax"] == expected_tax_with_idx

    gain_without_idx = net_sale - D("1_000_000") - D("200_000")
    expected_tax_without_idx = (max(gain_without_idx, D(0)) * D("0.125")).quantize(D("0.01"))
    assert resp.option_without_indexation["tax"] == expected_tax_without_idx

    assert resp.tax_amount == expected_tax_with_idx
    assert resp.tax_rate == D("0.20")


def test_immovable_property_post_july_2024_flat_rate():
    req = CapitalGainsRequest(
        asset_type=AssetType.immovable_property,
        purchase_date=date(2024, 8, 1),
        sale_date=date(2027, 1, 1),
        purchase_cost=D("1_000_000"),
        sale_consideration=D("1_200_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is True
    assert resp.tax_rate == D("0.125")
    assert resp.taxable_gain == D("200_000")
    assert resp.tax_amount == D("25_000")
    assert resp.indexed_cost is None


def test_gold_ltcg_pre_july_2024():
    req = CapitalGainsRequest(
        asset_type=AssetType.gold,
        purchase_date=date(2019, 4, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("800_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is True
    assert resp.recommended_option in ("with_indexation", "without_indexation")
    assert resp.tax_amount >= D(0)


def test_unlisted_shares_stcg_slab_rate():
    req = CapitalGainsRequest(
        asset_type=AssetType.unlisted_shares,
        purchase_date=date(2024, 1, 1),
        sale_date=date(2024, 12, 1),
        purchase_cost=D("200_000"),
        sale_consideration=D("250_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is False
    assert resp.classification == "STCG"
    assert resp.tax_rate is None
    assert resp.tax_amount == D(0)
    assert resp.taxable_gain == D("50_000")


def test_unlisted_shares_ltcg_pre_july_2024():
    req = CapitalGainsRequest(
        asset_type=AssetType.unlisted_shares,
        purchase_date=date(2019, 4, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("200_000"),
        sale_consideration=D("500_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.is_long_term is True
    assert resp.tax_amount > D(0)


def test_capital_gains_with_expenses():
    req = CapitalGainsRequest(
        asset_type=AssetType.listed_equity,
        purchase_date=date(2022, 1, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("700_000"),
        expenses_on_transfer=D("5_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.capital_gain == D("195_000")
    assert resp.taxable_gain == D("70_000")
    assert resp.tax_amount == D("8_750")


def test_capital_gains_zero_gain():
    req = CapitalGainsRequest(
        asset_type=AssetType.listed_equity,
        purchase_date=date(2022, 1, 1),
        sale_date=date(2024, 6, 1),
        purchase_cost=D("500_000"),
        sale_consideration=D("500_000"),
    )
    resp = compute_capital_gains(req)
    assert resp.tax_amount == D(0)
