# DTAA Data Sourcing TODO

This file tracks the treaty values that are **not yet sourced** in the
`app.services.nri_engine` DTAA explorer.  Per the project guardrail, no
rate, threshold or treaty value has been invented.

## Sourcing authority
- Signed India DTAA texts (incometax.gov.in → International Taxation → DTAA)
- CBDT notifications / protocols amending each treaty
- Multilateral Instrument (MLI) reservations/notifications

## Outstanding items

### 1. India–USA DTAA
- [ ] Dividend withholding rates (Article 10) including beneficial ownership and shareholding thresholds
- [ ] Interest withholding rates (Article 11)
- [ ] Royalty withholding rates (Article 12)
- [ ] Fees for technical services rates (Article 12)
- [ ] Capital-gains article exceptions (e.g., immovable-property clause, 183-day rule for shares)

### 2. India–UAE DTAA
- [ ] Dividend rates (Article 10)
- [ ] Interest rates (Article 11)
- [ ] Royalty / FTS rates (Article 12)
- [ ] Capital-gains tie-breaker for shares deriving value from immovable property
- [ ] Impact of India-UAE CEPA on services / royalty classifications

### 3. India–UK DTAA
- [ ] Dividend rates (Article 10)
- [ ] Interest rates (Article 11)
- [ ] Royalty / FTS rates (Article 12)
- [ ] Capital-gains article

### 4. India–Canada DTAA
- [ ] Dividend rates (Article 10)
- [ ] Interest rates (Article 11)
- [ ] Royalty / FTS rates (Article 12)
- [ ] Capital-gains article

### 5. India–Australia DTAA
- [ ] Dividend rates (Article 10)
- [ ] Interest rates (Article 11)
- [ ] Royalty / FTS rates (Article 12)
- [ ] Capital-gains article (including ECTA impact)

### 6. India–Singapore DTAA
- [ ] Dividend rates (Article 10)
- [ ] Interest rates (Article 11)
- [ ] Royalty / FTS rates (Article 12)
- [ ] Capital-gains article and the "shares deriving value from immovable property" clause

## What the engine does today
The DTAA explorer returns the treaty metadata, documentation requirements
(TRC + Form 10F) and tie-breaker rule for the six top corridors.  All
withholding rates are returned as `None` with a `ca_review_required` flag.
Once rates are sourced, populate `_DTAA_TREATIES` in
`app/services/nri_engine.py` and remove the corresponding TODO item here.
