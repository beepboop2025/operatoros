# Phase 1 — Tax Engine Test Findings

## Calculation disagreements (test expected vs. engine output)

After deriving expected values from the rules encoded in
`backend/app/services/tax_engine.py` + `backend/app/utils/tax_constants.py`,
no internal-calculation disagreements were found in the tested pure functions.
All pytest assertions pass without weakening tests.

## Suspected rule gaps / limitations observed

These are **not** changed in Phase 1 because they either require legal-content
verification or are outside the scope of tax-engine unit tests. They are
recorded here for follow-up review.

1. **Agricultural income is ignored in slab computation.**
   - `compute_income_tax` does not add `agricultural_income` to normal income.
   - The code comments state it is exempt but affects slab rates if > ₹5,000.
   - Current behavior: it has no effect on tax at all.

2. **TDS thresholds are treated as binary on/off switches.**
   - For sections such as `194IA` (consideration ≥ ₹50 lakh), `194A` (senior
     citizen threshold ₹50,000), and `194Q` (purchase > ₹50 lakh), the engine
     applies the rate to the **full** payment once the threshold is crossed.
   - The usual legal rule is TDS on the amount **exceeding** the threshold.
   - Test coverage documents the current behavior; if the legal rule is intended,
     this is a calculation gap.

3. **New-regime Section 87A rebate excludes special-rate income.**
   - Rebate eligibility is checked against `total_income_normal` only, which
     excludes `short_term_capital_gains_equity` and `long_term_capital_gains`.
   - If the rebate limit is meant to apply to total taxable income, the engine
     may grant rebate in cases where it should not.

4. **Surcharge on capital gains is not capped for equity gains.**
   - The code applies the surcharge rate to the entire tax after rebate.
   - For LTCG/STCG on listed equity/equity MFs, the surcharge is legally capped
     at 15% on those components.

5. **CII value for FY 2025-26 is marked as an estimate.**
   - `backend/app/utils/cii_table.py` notes the value will need updating when
     CBDT notifies the official figure.
