"""
Indian Income Tax constants for AY 2025-26 and AY 2026-27.

All monetary values are in INR (₹).  Slabs are represented as lists of
(lower_bound, upper_bound, rate) tuples where *upper_bound* is exclusive
(use ``float('inf')`` for the last bracket).

Source references:
  - Finance Act 2024 (for AY 2025-26)
  - Finance Act 2025 / Union Budget 2025 (for AY 2026-27)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
#  Type aliases
# --------------------------------------------------------------------------- #

Slab = Tuple[Decimal, Decimal, Decimal]          # (lower, upper, rate)
SlabTable = List[Slab]

INF = Decimal("Infinity")

# Helper — build Decimal slabs from plain numbers for readability
def _slabs(raw: list[tuple[int | float, int | float, float]]) -> SlabTable:
    return [
        (Decimal(str(lo)), Decimal(str(hi)) if hi != float("inf") else INF, Decimal(str(r)))
        for lo, hi, r in raw
    ]


# =========================================================================== #
#  NEW TAX REGIME SLABS
# =========================================================================== #

# AY 2025-26 (Finance Act 2024, Section 115BAC as amended)
NEW_REGIME_SLABS_AY2025 = _slabs([
    (0,       300_000,  0.00),
    (300_000, 700_000,  0.05),
    (700_000, 1_000_000, 0.10),
    (1_000_000, 1_200_000, 0.15),
    (1_200_000, 1_500_000, 0.20),
    (1_500_000, float("inf"), 0.30),
])

# AY 2026-27 (Union Budget 2025 — new slabs effective FY 2025-26)
NEW_REGIME_SLABS_AY2026 = _slabs([
    (0,         400_000,   0.00),
    (400_000,   800_000,   0.05),
    (800_000,   1_200_000, 0.10),
    (1_200_000, 1_600_000, 0.15),
    (1_600_000, 2_000_000, 0.20),
    (2_000_000, 2_400_000, 0.25),
    (2_400_000, float("inf"), 0.30),
])

NEW_REGIME_SLABS: Dict[str, SlabTable] = {
    "2025-26": NEW_REGIME_SLABS_AY2025,
    "2026-27": NEW_REGIME_SLABS_AY2026,
}


# =========================================================================== #
#  OLD TAX REGIME SLABS  (unchanged across AY 2025-26 / 2026-27)
# =========================================================================== #

# Age < 60
OLD_REGIME_SLABS_BELOW_60 = _slabs([
    (0,         250_000,   0.00),
    (250_000,   500_000,   0.05),
    (500_000,   1_000_000, 0.20),
    (1_000_000, float("inf"), 0.30),
])

# Age 60-79 (Senior Citizen)
OLD_REGIME_SLABS_60_TO_80 = _slabs([
    (0,         300_000,   0.00),
    (300_000,   500_000,   0.05),
    (500_000,   1_000_000, 0.20),
    (1_000_000, float("inf"), 0.30),
])

# Age 80+ (Super Senior Citizen)
OLD_REGIME_SLABS_80_PLUS = _slabs([
    (0,         500_000,   0.00),
    (500_000,   1_000_000, 0.20),
    (1_000_000, float("inf"), 0.30),
])

OLD_REGIME_SLABS: Dict[str, SlabTable] = {
    "below_60":  OLD_REGIME_SLABS_BELOW_60,
    "60_to_80":  OLD_REGIME_SLABS_60_TO_80,
    "80_plus":   OLD_REGIME_SLABS_80_PLUS,
}


# =========================================================================== #
#  STANDARD DEDUCTION
# =========================================================================== #

STANDARD_DEDUCTION_NEW_REGIME = Decimal("75000")   # AY 2025-26 onwards
STANDARD_DEDUCTION_OLD_REGIME = Decimal("50000")


# =========================================================================== #
#  SECTION 87A — REBATE
# =========================================================================== #

# Old regime — rebate of ₹12,500 if total income ≤ ₹5 lakh
REBATE_87A_OLD_LIMIT = Decimal("500000")
REBATE_87A_OLD_MAX   = Decimal("12500")

# New regime — AY 2025-26: rebate ₹25,000 if total income ≤ ₹7 lakh
REBATE_87A_NEW_AY2025_LIMIT = Decimal("700000")
REBATE_87A_NEW_AY2025_MAX   = Decimal("25000")

# New regime — AY 2026-27: rebate ₹60,000 if total income ≤ ₹12 lakh
REBATE_87A_NEW_AY2026_LIMIT = Decimal("1200000")
REBATE_87A_NEW_AY2026_MAX   = Decimal("60000")

REBATE_87A_NEW: Dict[str, Dict[str, Decimal]] = {
    "2025-26": {"limit": REBATE_87A_NEW_AY2025_LIMIT, "max_rebate": REBATE_87A_NEW_AY2025_MAX},
    "2026-27": {"limit": REBATE_87A_NEW_AY2026_LIMIT, "max_rebate": REBATE_87A_NEW_AY2026_MAX},
}


# =========================================================================== #
#  SURCHARGE RATES
# =========================================================================== #

# Old regime surcharge rates on income tax
# (income_lower, income_upper, surcharge_rate)
OLD_REGIME_SURCHARGE = _slabs([
    (0,             5_000_000,   0.00),
    (5_000_000,    10_000_000,   0.10),
    (10_000_000,   20_000_000,   0.15),
    (20_000_000,   50_000_000,   0.25),
    (50_000_000,   float("inf"), 0.37),
])

# New regime — max surcharge capped at 25%
NEW_REGIME_SURCHARGE = _slabs([
    (0,             5_000_000,   0.00),
    (5_000_000,    10_000_000,   0.10),
    (10_000_000,   20_000_000,   0.15),
    (20_000_000,   float("inf"), 0.25),   # capped
])


# =========================================================================== #
#  HEALTH & EDUCATION CESS
# =========================================================================== #

CESS_RATE = Decimal("0.04")   # 4% on tax + surcharge


# =========================================================================== #
#  CHAPTER VI-A DEDUCTIONS  (Old Regime)
# =========================================================================== #

# Section 80C — Life insurance, PPF, ELSS, NSC, etc.
SEC_80C_LIMIT = Decimal("150000")

# Section 80CCC (included within 80C limit)
SEC_80CCC_LIMIT = Decimal("150000")

# Section 80CCD(1) — Employee contribution to NPS (included in 80C limit)
SEC_80CCD1_LIMIT = Decimal("150000")

# Section 80CCD(1B) — Additional NPS deduction
SEC_80CCD1B_LIMIT = Decimal("50000")

# Section 80CCD(2) — Employer NPS contribution (no overall cap — 10%/14% of salary)
# Note: 80CCD(2) is available under BOTH old and new regime

# Section 80D — Medical Insurance
SEC_80D_SELF_BELOW_60 = Decimal("25000")
SEC_80D_SELF_SENIOR = Decimal("50000")        # self/spouse age ≥ 60
SEC_80D_PARENTS_BELOW_60 = Decimal("25000")
SEC_80D_PARENTS_SENIOR = Decimal("50000")      # parent age ≥ 60
SEC_80D_MAX_TOTAL = Decimal("100000")          # max when both self + parents are senior

# Section 80DD — Disabled dependent
SEC_80DD_NORMAL = Decimal("75000")
SEC_80DD_SEVERE = Decimal("125000")            # 80% or more disability

# Section 80E — Interest on education loan (no upper limit)
SEC_80E_LIMIT = None  # full interest deductible

# Section 80EEA — Interest on home loan (first-time buyer, stamp value ≤ ₹45 lakh)
SEC_80EEA_LIMIT = Decimal("150000")

# Section 80G — Donations (50% or 100% deduction, with/without limit)

# Section 80GG — Rent paid (no HRA)
SEC_80GG_LIMIT = Decimal("60000")   # ₹5,000/month

# Section 80TTA — Interest on savings (non-senior citizens)
SEC_80TTA_LIMIT = Decimal("10000")

# Section 80TTB — Interest on deposits (senior citizens ≥ 60)
SEC_80TTB_LIMIT = Decimal("50000")

# Section 80U — Disability of self
SEC_80U_NORMAL = Decimal("75000")
SEC_80U_SEVERE = Decimal("125000")


# =========================================================================== #
#  HRA EXEMPTION (Section 10(13A))
# =========================================================================== #

HRA_METRO_PERCENT = Decimal("0.50")    # 50% of (basic + DA) for metro cities
HRA_NON_METRO_PERCENT = Decimal("0.40")  # 40% for non-metro
HRA_SALARY_PERCENT = Decimal("0.10")    # 10% of salary subtracted from rent


# =========================================================================== #
#  CAPITAL GAINS TAX RATES (Post Finance Act 2024, effective 23 July 2024)
# =========================================================================== #

# Long-term capital gains — Listed equity / equity-oriented MF
LTCG_EQUITY_RATE = Decimal("0.125")          # 12.5%
LTCG_EQUITY_EXEMPTION = Decimal("125000")    # ₹1.25 lakh per year

# Short-term capital gains — Listed equity / equity-oriented MF
STCG_EQUITY_RATE = Decimal("0.20")           # 20%

# Long-term capital gains — Other assets (property, gold, unlisted, debt MF)
LTCG_OTHER_RATE = Decimal("0.125")           # 12.5% (indexation removed post July 2024)

# LTCG other — pre-July 2024 acquisitions (grandfathering: choice of 20% with
# indexation OR 12.5% without indexation, whichever is lower)
LTCG_OTHER_RATE_WITH_INDEXATION = Decimal("0.20")

# Short-term capital gains — Other assets  (at slab rates)
STCG_OTHER_RATE = None  # taxed at applicable slab rates

# Holding periods for LTCG classification
HOLDING_PERIOD_LISTED_EQUITY_MONTHS = 12         # > 12 months
HOLDING_PERIOD_UNLISTED_SHARES_MONTHS = 24       # > 24 months
HOLDING_PERIOD_IMMOVABLE_PROPERTY_MONTHS = 24    # > 24 months
HOLDING_PERIOD_OTHER_MONTHS = 36                 # > 36 months (gold, debt MF, etc.)
# Post Budget 2024 — all non-listed/non-equity assets: 24 months for LTCG
HOLDING_PERIOD_OTHER_MONTHS_NEW = 24


# =========================================================================== #
#  ADVANCE TAX INSTALLMENTS
# =========================================================================== #

ADVANCE_TAX_SCHEDULE = [
    {"due_date_label": "15 June",  "cumulative_percent": Decimal("0.15")},
    {"due_date_label": "15 September", "cumulative_percent": Decimal("0.45")},
    {"due_date_label": "15 December",  "cumulative_percent": Decimal("0.75")},
    {"due_date_label": "15 March",     "cumulative_percent": Decimal("1.00")},
]


# =========================================================================== #
#  INTEREST U/S 234A, 234B, 234C
# =========================================================================== #

INTEREST_234A_RATE = Decimal("0.01")   # 1% per month (or part thereof)
INTEREST_234B_RATE = Decimal("0.01")   # 1% per month
INTEREST_234C_RATE = Decimal("0.01")   # 1% per month


# =========================================================================== #
#  LATE FILING FEE — Section 234F
# =========================================================================== #

LATE_FEE_234F_ABOVE_5L = Decimal("5000")
LATE_FEE_234F_UPTO_5L  = Decimal("1000")


# =========================================================================== #
#  DEPRECIATION RATES (Common WDV rates under IT Act)
# =========================================================================== #

DEPRECIATION_RATES: Dict[str, Decimal] = {
    "building_residential":    Decimal("0.05"),     # 5%
    "building_non_residential": Decimal("0.10"),    # 10%
    "furniture_fittings":      Decimal("0.10"),     # 10%
    "plant_machinery_general": Decimal("0.15"),     # 15%
    "plant_machinery_higher":  Decimal("0.30"),     # 30% (computers, etc.)
    "motor_vehicle":           Decimal("0.15"),     # 15%
    "intangible_assets":       Decimal("0.25"),     # 25% (patents, copyrights, etc.)
}

# Additional depreciation for new plant & machinery (manufacturing)
ADDITIONAL_DEPRECIATION_RATE = Decimal("0.20")     # 20%
