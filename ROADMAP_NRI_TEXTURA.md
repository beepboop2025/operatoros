# OperatorOS → Cross-Border Tax Platform for NRIs (Sales-Ready Redesign + New Modules)

Direction: reposition OperatorOS from a domestic-India CA tool into a **cross-border
taxation platform that NRIs and global Indians want to use**, with a premium **Textura**
dark interface and a live international-tax radar. Execute AFTER the current engineering
swarm (Phases 1–4) merges into `feat/free-llm-router`.

## Hard sequencing
1. Current swarm (P1 tests, P2 backend logic, P3 infra, P4 frontend) finishes → merge 4
   branches.
2. THEN Phase 6 (design system + reskin) and Phase 7 (NRI modules) — they touch the same
   frontend/backend files the swarm is editing, so they cannot run concurrently with it.
3. Phase 8 (world-affairs tracker) can be built partly in `social_scraper` in parallel.

## Domain-accuracy guardrail (applies to all of Phase 7)
Tax logic must never be invented. Pure computation (residential status, FTC, 195 TDS math)
is fair to build + unit-test. But **every rate, threshold, DTAA treaty value, and customs
duty number must come from an authoritative source** (incometax.gov.in, the DTAA text, the
Customs Tariff) and be marked for CA review. When a value isn't available, emit it to a
`*_TODO.md`, do not guess. India is mid-transition: **Income-tax Act 2025 / Rules 2026** are
in force and **NRI residency rules change again from 1 Apr 2026** — encode rules as
versioned/AY-keyed data, not hardcoded constants.

---

## PHASE 6 — Textura design system + landing + full dashboard reskin (premium dark)

**Design tokens** (from `~/beepboop-site`, the established Textura identity):
- bg `#000`; panels `#0a0a0a`/`#0e0e0e`; text `#FAFAFA`; dim `#C7C7C7` / `#6a6a6a`
- accent (icy) `#A1ECFF`; warm (peach) `#FFAB98`; line `rgba(250,250,250,.12)`
- gradient `linear-gradient(241deg, #FFAB98, #A1ECFF)`
- fonts: **Gilda Display** (display/headings, italic emphasis) + **Lato** (UI/data)
- signature ease `cubic-bezier(0.16,1,0.3,1)`

1. **Theme layer**: define the tokens as Tailwind v4 theme vars + CSS custom properties.
   One source of truth consumed by every component.
2. **`<TexturaBackground>` component** (the "Textura background"): pure-black base →
   two blurred gradient orbs (peach/cyan, `blur(120px)`, opacity ~.14) → film-grain +
   radial vignette overlay → optional cursor-tracking radial glow (`--mx/--my`). Must sit
   behind content with `pointer-events:none` and respect `prefers-reduced-motion`.
3. **Marketing landing** (`/` or `/welcome`, public, NRI-targeted — see Phase 7 copy):
   Gilda hero with gradient-clip emphasis, smooth-scroll sections (features, modules,
   pricing, trust/CA-backed, CTA), micro-interactions on the signature ease. Match the
   polish bar of the VitalChain landing but keep it CSS/React-spring (no heavy 3D required
   unless cheap).
4. **Dashboard reskin** — apply the dark theme to all existing screens (Dashboard,
   Clients, ClientDetail, TaxComputer, QueryChat, DocumentManager, NoticeManager,
   ComplianceCalendar, Login) + the new NRI screens. Build shared primitives first:
   `Panel`, `StatCard`, `DataTable`, `Field` (accent focus ring), `Button`
   (gradient/ghost), `Tabs`, `Toast` — then refactor screens onto them. Recharts theming:
   dark grid, accent/peach series, legible axis contrast.
5. **Motion**: page/section transitions + list stagger on the signature ease; keep it
   smooth and restrained (this is a working tool, not a showreel). All AA-contrast,
   keyboard-navigable, reduced-motion aware.

**Gate:** `npm run typecheck && lint && build` pass; every screen on the shared dark
primitives; landing + app visually cohesive.

---

## PHASE 7 — NRI cross-border taxation modules

Each module = backend pure-logic engine + schema + route + tests + a reskinned screen.
Reuse the existing `tax_engine.py` patterns (Decimal, request→response dataclasses).

1. **Residential Status Determiner** — inputs: days in India (current FY + prior 4 FYs),
   citizenship/PIO, Indian-source income, whether tax-resident elsewhere. Output:
   Resident / RNOR / NRI / **Deemed Resident**, the controlling rule, and the resulting
   **scope of taxable income**. Encodes the 182-day, 60+365-day, the ₹15L→120-day, the
   employment→182-day, and the deemed-resident rules — AY-keyed (pre/post Apr-2026).
   Pure + heavily unit-tested.
2. **DTAA Explorer** — treaty-partner country → article rates (dividends/interest/
   royalty/FTS/capital gains), residency tie-breaker, and the **TRC + Form 10F**
   requirement. Data-driven treaty table (start with top NRI corridors: USA, UAE, UK,
   Canada, Australia, Singapore). CA-verified; missing treaties → `DTAA_TODO.md`.
3. **Section 195 / Repatriation Toolkit** — TDS on payments to NRIs (no threshold; rate
   per Finance Act or DTAA, whichever lower if TRC), **Form 15CA/15CB** workflow,
   lower/nil-deduction certificate (197 / Form 15E), and NRI **property-sale TDS**
   (LTCG 12.5% + surcharge/cess for FY25-26). Repatriation limits (USD 1M scheme) as
   informational guidance.
4. **Foreign Tax Credit (FTC)** — Rule 128 / **Form 67** calculator: per-country foreign
   income + foreign tax paid → allowable FTC (lower of Indian tax on that income vs foreign
   tax), DTAA vs non-DTAA, with the before-due-date filing reminder. Pure + tested.
5. **Customs & Tariffs** — HSN-keyed import-duty calculator: **BCD + Social Welfare
   Surcharge + IGST** (and cesses), FTA/preferential-rate flags, and a tariff-change feed
   (ties into Phase 8). Data-driven from the Customs Tariff; CA/CHA-verified; gaps →
   `TARIFF_TODO.md`.
6. **GST (cross-border framing)** — already implemented; extend with import IGST,
   export/LUT zero-rating, OIDAR, and place-of-supply for cross-border services. Reuse
   existing `compute_gst`.

**Gate per module:** pure engine unit-tested; route returns typed response; screen wired;
any unsourced rate/treaty value listed in the module's `*_TODO.md` for CA review.

---

## PHASE 8 — International Tax Intelligence (the "world affairs radar")

Goal: a live dashboard panel + alerts tracking global tax/trade developments relevant to
NRIs and cross-border clients (OECD BEPS / **Pillar Two**, DTAA amendments, foreign budget
changes, US/EU/UAE tax & **tariff/trade actions**, RBI/FEMA circulars).

**Reuse, don't rebuild:**
- `social_scraper` already scrapes 15 sources with a 6-source news fallback chain, a
  destination router, and financial NLP. Add: (a) an **"international-tax" classifier
  topic**, (b) a **push connector to OperatorOS** (mirror the existing DragonScope/LiquiFi
  Redis+API connectors).
- `free-llm-router` summarizes + tags each item (jurisdiction, topic, NRI-impact score).
- OperatorOS side: a `tax_intel` ingest endpoint + table + a Textura dashboard panel
  ("World Tax Radar") with filters (jurisdiction/topic/impact) and per-client relevance
  alerts. Mirror the existing alert-engine pattern.

**Gate:** items flow scraper → router → OperatorOS panel; each carries source URL +
LLM summary + jurisdiction/impact tags; failures degrade soft (empty, not crash).

---

## Positioning / copy (so NRIs are interested) — for the Phase 6 landing
- Hero: *"Cross-border tax, finally clear."* — for NRIs, returning Indians, and global
  founders.
- Lead with the pains NRIs actually feel: **Am I a resident this year?** (residency
  determiner), **Am I being double-taxed?** (DTAA + FTC), **How much TDS on my property
  sale / remittance?** (195), **What changed in the law while I was away?** (World Tax
  Radar).
- Trust: CA-reviewed computations, India + international coverage, FEMA/RBI aware.
- Make the residency determiner + a DTAA lookup the **free interactive hook** on the
  landing (lead-gen), gated deeper features behind signup.

## Out of scope / human-owned
- Authoring DTAA treaty text, customs duty rates, or any legal value from memory
  (guardrail above).
- Actual legal/tax sign-off — every computation surfaces a "CA review" affordance.
