# Customs / Tariff Data Sourcing TODO

This file tracks the customs duty numbers that are **not yet sourced** in the
`app.services.nri_engine` customs/tariff calculator.  Per the project guardrail,
no BCD, cess, SWS or IGST rate has been invented.

## Sourcing authority
- Customs Tariff Act, 1975 (as amended)
- Central Excise Tariff (for HSN classification)
- Customs Notification No. 12/2024-Customs (N.T.) and subsequent amendments
- IGST Act / notifications for import IGST rates
- FTA notification texts (ASEAN, SAFTA, India-UAE CEPA, India-UK EPA, India-Australia ECTA, Singapore CECA)

## Outstanding items

### 1. HSN-specific BCD rates
- [ ] Populate `_CUSTOMS_TARIFF_RATES` with BCD rates by HSN code / chapter prefix
- [ ] Add agriculture / dairy chapters
- [ ] Add electronics / mobile phones chapter (e.g., 8517)
- [ ] Add textiles chapter
- [ ] Add machinery / industrial goods chapters
- [ ] Add automobile chapter (8703)

### 2. Social Welfare Surcharge (SWS)
- [ ] Confirm whether SWS applies at 10% of BCD for every HSN or is exempted under specific notifications
- [ ] Add SWS exemption flags per chapter

### 3. Cesses
- [ ] Health & education cess on imports (currently not levied as separate SWS)
- [ ] Agriculture Infrastructure and Development Cess (AIDC) where applicable
- [ ] Other product-specific cesses (e.g., road & infrastructure cess on petrol/diesel)

### 4. Import IGST rates
- [ ] Map HSN codes to IGST rates for imports (usually same as domestic GST rate)
- [ ] Handle exempt / nil-rated imports

### 5. FTA / preferential rates
- [ ] Build preferential BCD rate table for each FTA
- [ ] Add Rules of Origin check (qualifying criteria are outside pure math)
- [ ] Add FTA code validation against `_RECOGNISED_FTAS`

### 6. Computed-landed-cost assumptions
- [ ] Confirm IGST base includes BCD + SWS + cess (notification-level detail)
- [ ] Add anti-dumping / safeguard duty handling (separate line items)

## What the engine does today
The customs engine computes landed cost only when **all required rates are
provided as overrides**.  When a rate is missing it returns `None` for the
computed totals and lists the missing rates.  Once tariff data is sourced,
populate `_CUSTOMS_TARIFF_RATES` in `app/services/nri_engine.py` and remove
corresponding TODO items here.
