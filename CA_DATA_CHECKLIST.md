# OperatorOS — CA Data-Sourcing Checklist

**Purpose.** The NRI cross-border engines are built and tested, but — by design — they
ship with **no invented tax values**. They return `null` + `ca_review_required: true`
until the tables below are filled from authoritative sources. This document is the
**single worksheet a CA fills in**; an engineer (or Kimi) then transcribes the confirmed
values into `backend/app/services/nri_engine.py`.

**Ground rule for whoever fills this:** every value needs a **source citation** (Act
section / treaty article / notification number + date). If a value is uncertain, leave it
blank and note why — a blank is safe (engine returns `null`); a wrong value silently
corrupts client advice.

**How values reach the code (for the engineer):**
- DTAA rates → `_DTAA_TREATIES` dict (`nri_engine.py:331`); set the per-income-type rates
  and flip `ca_review_required=False` once a treaty is fully sourced.
- Customs rates → `_CUSTOMS_TARIFF_RATES` dict (`nri_engine.py:835`, currently `{}`).
- §195 domestic rates → the Section 195 rate table (currently override-only).
- Residency thresholds → confirm the AY-2026-27 rule constants.

---

## 1. DTAA withholding rates — 6 priority corridors

For **each** treaty, fill the table. Rates are the **treaty-capped** withholding %; the
engine applies the lower of treaty vs domestic (§195) when a valid TRC + Form 10F exist.

### Template (repeat per country: USA, UAE, UK, Canada, Australia, Singapore)

| Income type | Treaty article | Rate % | Conditions / thresholds | Source (article + protocol/MLI) |
|---|---|---|---|---|
| Dividends (general) | Art. 10 |  | beneficial owner; non-portfolio |  |
| Dividends (substantial holding) | Art. 10 |  | e.g. ≥10%/≥25% shareholding |  |
| Interest (general) | Art. 11 |  |  |  |
| Interest (banks/govt exemptions) | Art. 11 |  | exempt cases |  |
| Royalties | Art. 12 |  |  |  |
| Fees for technical services (FTS) | Art. 12/12A |  | "make available" clause? |  |
| Capital gains — shares | Art. 13 |  | immovable-property-rich clause; 183-day |  |
| Capital gains — immovable property | Art. 13 |  | taxable in situs state |  |

**Per-corridor notes to capture:**
- **USA:** Art. 12 FTS "make available"; LOB article; treaty 15%/25% dividend tiers.
- **UAE:** post **CEPA** services/royalty classification; TRC mandatory; tie-breaker for
  property-rich shares.
- **UK / Canada / Australia / Singapore:** confirm whether **MLI** changed the PPT/dividend
  holding-period; Singapore & UK property-rich-shares clause; Australia **ECTA** impact.

**Cross-cutting (confirm once):**
- [ ] Surcharge & cess applicability **on top of** treaty rate (or is treaty rate
  all-inclusive?)
- [ ] TRC (Tax Residency Certificate) + **Form 10F** + **Form 67** filing prerequisites
- [ ] Grandfathering for pre-1 Apr 2017 share acquisitions (where relevant)

---

## 2. Section 195 — domestic TDS rates on payments to NRIs

The engine needs the **Finance Act 2025/2026 First Schedule** §195 rates (used when no
valid treaty rate applies). Fill per payment type:

| Payment type | Domestic rate % | Surcharge/cess added? | Threshold (if any) | Source (Finance Act / section) |
|---|---|---|---|---|
| Interest (general) |  |  | none (§195 has no threshold) |  |
| Dividend |  |  |  |  |
| Royalty |  |  |  |  |
| FTS |  |  |  |  |
| LTCG — listed equity |  |  | 12.5% (FY25-26?) confirm |  |
| LTCG — other assets |  |  |  |  |
| STCG — listed equity (111A) |  |  |  |  |
| Rent (NRI landlord) |  |  |  |  |
| Property purchase from NRI |  |  | LTCG 12.5% + surcharge — confirm |  |

- [ ] Confirm **no minimum threshold** under §195 (unlike 194-series)
- [ ] Confirm Form **15CA part** routing (A/B/C/D) + when **15CB** (CA cert) is mandatory
- [ ] Lower/nil-deduction certificate route (§197 / Form 13 / Form 15E)

---

## 3. Customs / Tariff rates by HSN

Populate per HSN chapter/code the client base actually imports. Start with the high-volume
chapters; this can grow over time.

| HSN code/chapter | Description | BCD % | SWS % (usu. 10% of BCD) | AIDC/other cess % | Import IGST % | FTA preferential BCD % (which FTA) | Source (Customs Tariff / notification) |
|---|---|---|---|---|---|---|---|
| 8517 | Phones/telecom |  |  |  |  |  |  |
| 8703 | Motor vehicles |  |  |  |  |  |  |
| (textiles ch. 50-63) |  |  |  |  |  |  |  |
| (machinery ch. 84-85) |  |  |  |  |  |  |  |
| (agri/dairy ch. 1-24) |  |  |  |  |  |  |  |

**Confirm once:**
- [ ] IGST base = assessable value + BCD + SWS + cess? (notification-level)
- [ ] SWS exemptions by notification (which HSNs are exempt)
- [ ] FTAs in scope: ASEAN, SAFTA, **UAE-CEPA**, **UK-EPA**, **Australia-ECTA**, Singapore-CECA
- [ ] Rules-of-Origin: which is a *checkbox* in-app vs needs manual CA determination
- [ ] Anti-dumping / safeguard duties handled as separate line items?

---

## 4. Residential-status rule constants (verify, don't re-derive)

The engine encodes these — **confirm against the gazetted Income-tax Act 2025 / Finance
Act 2026** before go-live:

- [ ] 182-day rule (resident) — unchanged
- [ ] 60-day + 365-day (prior 4 yrs) rule — unchanged
- [ ] **120-day** substituted threshold for citizens/PIO with **Indian income > ₹15L** —
  confirm effective AY and that ₹15L is "income other than foreign sources"
- [ ] 182-day substitution for Indian citizens leaving for employment
- [ ] **Deemed resident**: Indian citizen, Indian income > ₹15L, **not tax-resident
  anywhere** → deemed RNOR scope
- [ ] RNOR scope: foreign income exempt; confirm the two RNOR qualifying tests
- [ ] **Any change effective 1 Apr 2026** flagged in news — verify final law text

---

## 5. The 4 flagged calculation findings (decide treatment)

From `backend/PHASE1_FINDINGS.md` — these are existing-engine behaviours the tests
surfaced. **A CA decision is needed** on each (is current behaviour correct, or a bug to
fix?):

- [ ] **Agricultural income** ignored in slab-rate computation (partial-integration rule?)
- [ ] **TDS on full amount vs excess** over threshold (194IA/194A/194Q)
- [ ] **§87A rebate** eligibility vs special-rate (capital-gains) income
- [ ] **Surcharge cap (15%)** on listed-equity LTCG/STCG not applied

> When each row above is confirmed, tick it, cite the source, and hand back — the
> engineering side transcribes values into `nri_engine.py` / `tax_engine.py` and flips the
> `ca_review_required` flags off. Until then the app correctly shows "pending CA review"
> rather than a wrong number.
