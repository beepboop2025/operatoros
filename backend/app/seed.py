#!/usr/bin/env python3
"""
app/seed.py — Demo seed data for OperatorOS (India / NRI cross-border tax practice).

Populates a realistic, *non-empty* demo: one CA firm, two staff users, a spread of
Indian + NRI clients, and enough compliance tasks, notices, tax computations,
AuditMind queries, and World Tax Radar items that every dashboard screen looks alive.

Design notes:
  * ORM-based — uses the real SQLAlchemy models, so it can never drift from the schema
    (unlike the old raw-SQL version, which built a parallel fake `clients` table).
  * Idempotent — re-running it will not duplicate rows (keyed on firm slug / user email /
    client PAN; child rows are only created the first time their parent is created).
  * Date-relative — due dates / deadlines are computed from "today", so the compliance
    calendar always shows a believable mix of overdue, due-soon, and upcoming items.

Usage (inside the backend container, where WORKDIR is /app):
    python -m app.seed                 # seed an already-migrated DB
    python -m app.seed --create-tables # also create tables on a fresh DB (skips Alembic)

Locally:  cd backend && python -m app.seed [--create-tables]

Reads DATABASE_URL from the environment (defaults to the docker-compose service URL).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Make the `app` package importable whether run as `python -m app.seed` (preferred,
# from the backend WORKDIR) or directly as `python backend/app/seed.py`. The package
# root is the parent of this file's directory (backend/app -> backend).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select  # noqa: E402
from sqlalchemy import text as sa_text  # noqa: E402

from app.database import async_session_factory, engine  # noqa: E402
from app.middleware.auth import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    Client,
    ComplianceTask,
    Firm,
    Notice,
    Query,
    TaxComputation,
    TaxIntel,
    User,
)
from app.models.client import EntityType  # noqa: E402
from app.models.compliance import ComplianceStatus, TaskType  # noqa: E402
from app.models.computation import TaxRegime  # noqa: E402
from app.models.notice import NoticeStatus, NoticeType  # noqa: E402
from app.models.query import QueryType  # noqa: E402
from app.models.user import UserRole  # noqa: E402

TODAY = date.today()
NOW = datetime.now(timezone.utc)


def days(n: int) -> date:
    """A date `n` days from today (negative = past)."""
    return TODAY + timedelta(days=n)


# ── Demo login ────────────────────────────────────────────────────────────────
# A single shared demo account. Print at the end so it's easy to hand out.

DEMO_EMAIL = "demo@operatoros.in"
DEMO_PASSWORD = "OperatorOS#2026"


async def seed() -> None:
    async with async_session_factory() as db:
        # ── Firm (tenant) ──────────────────────────────────────────────────
        firm = await _get_or_create(
            db,
            Firm,
            match={"slug": "kapoor-mehta"},
            defaults=dict(
                name="Kapoor Mehta & Associates LLP, Chartered Accountants",
                slug="kapoor-mehta",
                address="No. 14, 100 Feet Road, Indiranagar, Bengaluru 560038, Karnataka",
                phone="+91 80 4123 7788",
                email="contact@kapoormehta.in",
                gstin="29AABCK1234M1Z5",
                is_active=True,
                settings_json={
                    "specialisation": ["NRI taxation", "DTAA", "FEMA", "GST"],
                    "default_regime": "new",
                },
            ),
        )
        await db.flush()

        # ── Users (staff) ──────────────────────────────────────────────────
        demo = await _get_or_create(
            db,
            User,
            match={"email": DEMO_EMAIL},
            defaults=dict(
                email=DEMO_EMAIL,
                full_name="CA Arjun Kapoor",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.admin,
                is_active=True,
                firm_id=firm.id,
            ),
        )
        associate = await _get_or_create(
            db,
            User,
            match={"email": "priya@operatoros.in"},
            defaults=dict(
                email="priya@operatoros.in",
                full_name="Priya Nair",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.associate,
                is_active=True,
                firm_id=firm.id,
            ),
        )
        await db.flush()

        # ── Clients (Indian entities + NRIs) ───────────────────────────────
        # (firm_name, contact, email, phone, pan, gstin, cin, entity_type, assignee, address)
        client_specs = [
            (
                "Tata Nexus Pvt Ltd", "Rohan Tata", "rohan@tatanexus.in", "+91 98860 11223",
                "AABCT1234N", "29AABCT1234N1Z9", "U72200KA2018PTC123456",
                EntityType.private_limited, demo,
                {"city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560066"},
            ),
            (
                "Infosys Vendor Solutions LLP", "Meera Iyer", "meera@ivs.in", "+91 99001 44556",
                "AABFI5678P", "29AABFI5678P1ZB", None,
                EntityType.llp, associate,
                {"city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560100"},
            ),
            (
                "Vikram Sethi (NRI — USA)", "Vikram Sethi", "vikram.sethi@gmail.com", "+1 408 555 0142",
                "AKLPS9012Q", None, None,
                EntityType.individual, demo,
                {"city": "San Jose", "state": "California", "country": "USA", "residency": "non-resident"},
            ),
            (
                "Anjali Rao (NRI — UAE)", "Anjali Rao", "anjali.rao@outlook.com", "+971 50 123 4567",
                "BNZPR3456R", None, None,
                EntityType.individual, associate,
                {"city": "Dubai", "country": "UAE", "residency": "non-resident"},
            ),
            (
                "Sharma HUF", "Suresh Sharma", "suresh.sharma@gmail.com", "+91 98200 77881",
                "AAEHS7890T", None, None,
                EntityType.huf, demo,
                {"city": "Mumbai", "state": "Maharashtra", "country": "India", "pincode": "400050"},
            ),
            (
                "Green Valley Traders", "Kiran Patel", "kiran@greenvalley.in", "+91 99099 33445",
                "AAGFG2345L", "24AAGFG2345L1Z7", None,
                EntityType.partnership, associate,
                {"city": "Ahmedabad", "state": "Gujarat", "country": "India", "pincode": "380015"},
            ),
            (
                "Deepak Menon", "Deepak Menon", "deepak.menon@gmail.com", "+91 98470 22113",
                "AXTPM6789K", None, None,
                EntityType.individual, demo,
                {"city": "Kochi", "state": "Kerala", "country": "India", "pincode": "682020"},
            ),
            (
                "Aarogya Charitable Trust", "Lakshmi Venkat", "trust@aarogya.org", "+91 80 2554 9090",
                "AAATA4567C", None, None,
                EntityType.trust, associate,
                {"city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560004"},
            ),
        ]

        clients: dict[str, Client] = {}
        for (firm_name, contact, email, phone, pan, gstin, cin, etype, assignee, addr) in client_specs:
            c = await _get_or_create(
                db,
                Client,
                match={"pan": pan},
                defaults=dict(
                    firm_name=firm_name,
                    contact_person=contact,
                    email=email,
                    phone=phone,
                    pan=pan,
                    gstin=gstin,
                    cin=cin,
                    entity_type=etype,
                    address_json=addr,
                    assigned_to=assignee.id,
                    firm_id=firm.id,
                    is_active=True,
                    onboarded_at=NOW - timedelta(days=120),
                ),
                created_flag=True,
            )
            clients[pan] = c
        await db.flush()

        # Only seed child rows for clients we created fresh (keeps reruns clean).
        fresh = [c for c in clients.values() if getattr(c, "_seed_created", False)]

        if fresh:
            await _seed_compliance(db, clients, demo, associate)
            await _seed_notices(db, clients, demo, associate)
            await _seed_computations(db, clients, demo)
            await _seed_queries(db, clients, demo, associate)

        # ── World Tax Radar (no FKs — seed if empty) ───────────────────────
        await _seed_tax_intel(db)

        await db.commit()

    print("\n" + "─" * 60)
    print("  Seed complete. Demo login:")
    print(f"    URL      : https://app.<your-domain>   (or http://localhost:5173)")
    print(f"    Email    : {DEMO_EMAIL}")
    print(f"    Password : {DEMO_PASSWORD}")
    print("─" * 60)


# ── Child seeders ───────────────────────────────────────────────────────────


async def _seed_compliance(db, clients, demo, associate) -> None:
    rows = [
        # (client_pan, type, due_date, AY, status, assignee_id, description)
        ("AABCT1234N", TaskType.gst_return, days(-3),
         "2026-27", ComplianceStatus.overdue, associate.id, "GSTR-3B for May 2026 — output tax ₹4.2L"),
        ("AABCT1234N", TaskType.tds_return, days(12),
         "2026-27", ComplianceStatus.in_progress, demo.id, "Form 26Q — Q1 FY2026-27 TDS on contractor payments"),
        ("AABFI5678P", TaskType.gst_return, days(8),
         "2026-27", ComplianceStatus.pending, associate.id, "GSTR-1 for May 2026 — B2B invoices pending reconciliation"),
        ("AKLPS9012Q", TaskType.itr_filing, days(40),
         "2026-27", ComplianceStatus.pending, demo.id, "ITR-2 for NRI — capital gains on Indian MF redemption + DTAA relief"),
        ("BNZPR3456R", TaskType.itr_filing, days(40),
         "2026-27", ComplianceStatus.pending, associate.id, "ITR-2 for NRI (UAE) — rental income from Pune property"),
        ("AAEHS7890T", TaskType.advance_tax, days(-6),
         "2026-27", ComplianceStatus.overdue, demo.id, "Advance tax Q1 (15%) — interest u/s 234C accruing"),
        ("AAGFG2345L", TaskType.tax_audit, days(101),
         "2025-26", ComplianceStatus.pending, associate.id, "Tax audit u/s 44AB — turnover ₹3.1 Cr"),
        ("AXTPM6789K", TaskType.itr_filing, days(40),
         "2026-27", ComplianceStatus.in_progress, demo.id, "ITR-1 — salaried, new regime, Form 16 received"),
        ("AAATA4567C", TaskType.roc_filing, days(25),
         "2025-26", ComplianceStatus.pending, associate.id, "Form 10B audit report for charitable trust"),
        ("AABCT1234N", TaskType.itr_filing, days(-15),
         "2025-26", ComplianceStatus.completed, demo.id, "ITR-6 FY2024-25 — filed and verified"),
    ]
    for (p, ttype, due, ay, status, assignee, desc) in rows:
        task = ComplianceTask(
            client_id=clients[p].id,
            task_type=ttype,
            description=desc,
            due_date=due,
            assessment_year=ay,
            status=status,
            assigned_to=assignee,
            completed_at=(NOW - timedelta(days=10)) if status == ComplianceStatus.completed else None,
        )
        db.add(task)


async def _seed_notices(db, clients, demo, associate) -> None:
    rows = [
        ("AABCT1234N", NoticeType.scrutiny_143_2, days(-20), days(10),
         NoticeStatus.under_review, demo.id,
         "Limited scrutiny — mismatch between GST turnover and ITR turnover for AY 2024-25. "
         "AO seeks reconciliation of ₹38L difference."),
        ("AKLPS9012Q", NoticeType.intimation_143_1, days(-9), None,
         NoticeStatus.response_drafted, demo.id,
         "Intimation u/s 143(1) — TDS credit u/s 195 not fully matched in 26AS; refund recomputed. "
         "Rectification 154 draft prepared."),
        ("AAGFG2345L", NoticeType.gst_asmt_10, days(-5), days(15),
         NoticeStatus.received, associate.id,
         "GST ASMT-10 — ITC mismatch between GSTR-3B and GSTR-2B for FY2025-26, ₹2.7L."),
        ("BNZPR3456R", NoticeType.information_133_6, days(-2), days(28),
         NoticeStatus.received, associate.id,
         "Notice u/s 133(6) — verification of source of funds for property purchase in Pune (NRI)."),
    ]
    for (p, ntype, ndate, deadline, status, assignee, summary) in rows:
        db.add(Notice(
            client_id=clients[p].id,
            notice_type=ntype,
            notice_date=ndate,
            response_deadline=deadline,
            summary=summary,
            status=status,
            assigned_to=assignee,
        ))


async def _seed_computations(db, clients, demo) -> None:
    rows = [
        ("AXTPM6789K", "2026-27", TaxRegime.new, Decimal("1850000"),
         {"standard_deduction": 75000, "80C": 0, "80CCD_1B": 0},
         Decimal("213840"),
         {"slabs": "new", "cess": 8225, "rebate_87A": 0, "notes": "Salaried, new regime default"}),
        ("AKLPS9012Q", "2026-27", TaxRegime.old, Decimal("2240000"),
         {"LTCG_112A": 180000, "80C": 150000, "DTAA_relief_us_90": 96000},
         Decimal("402480"),
         {"residential_status": "non-resident", "treaty": "India-USA DTAA Art. 13",
          "notes": "Foreign tax credit claimed via Form 67"}),
        ("AAEHS7890T", "2026-27", TaxRegime.old, Decimal("980000"),
         {"80C": 150000, "80D": 25000},
         Decimal("80600"),
         {"entity": "HUF", "notes": "Old regime — deductions optimised"}),
    ]
    for (p, ay, regime, gross, ded, liability, comp) in rows:
        db.add(TaxComputation(
            client_id=clients[p].id,
            assessment_year=ay,
            regime=regime,
            gross_income=gross,
            deductions_json=ded,
            tax_liability=liability,
            computation_json=comp,
            computed_by=demo.id,
        ))


async def _seed_queries(db, clients, demo, associate) -> None:
    rows = [
        (clients["AKLPS9012Q"].id, demo.id, QueryType.advisory,
         "An NRI client in the US sold Indian equity mutual funds held for 3 years. "
         "How is the LTCG taxed and can DTAA reduce it?",
         "Long-term capital gains on equity-oriented mutual funds (held > 12 months) are taxed "
         "u/s 112A at 12.5% on gains exceeding ₹1.25L (post-Budget 2024 rates). For a US-resident "
         "NRI, the India-USA DTAA (Art. 13) generally allows India to tax these gains, but the "
         "client may claim a foreign tax credit in the US. TDS u/s 196A/195 applies on redemption; "
         "claim excess via ITR-2. File Form 67 before the return to substantiate any FTC.",
         [{"source": "Income-tax Act, s.112A", "ref": "LTCG on equity MF"},
          {"source": "India-USA DTAA", "ref": "Article 13 — Capital Gains"},
          {"source": "Rule 128", "ref": "Foreign Tax Credit / Form 67"}],
         "openrouter/auditmind", 1840, 2310.5),
        (clients["BNZPR3456R"].id, associate.id, QueryType.procedural,
         "What are the TDS implications when an NRI in the UAE earns rent from a flat in Pune?",
         "Rent paid to an NRI is subject to TDS u/s 195 at the applicable slab rate (not the 31.2% "
         "blanket rate that applies to some heads), on the gross rent. The tenant must obtain a TAN "
         "and file Form 27Q quarterly, issuing Form 16A. The NRI can claim a lower/nil deduction "
         "certificate u/s 197. Since the UAE has no personal income tax, no FTC arises, but the "
         "India-UAE DTAA tie-breaker and residency (≥182 days) should be confirmed.",
         [{"source": "Income-tax Act, s.195", "ref": "TDS on payments to non-residents"},
          {"source": "Form 27Q / Form 16A", "ref": "Quarterly TDS return"},
          {"source": "s.197", "ref": "Lower deduction certificate"}],
         "openrouter/auditmind", 1520, 1980.2),
        (clients["AABCT1234N"].id, demo.id, QueryType.factual,
         "What is the due date for the tax audit report and ITR for a company for AY 2025-26?",
         "For a company subject to tax audit u/s 44AB, the audit report (Form 3CA/3CD) is due by "
         "30 September 2025, and the income-tax return (ITR-6) by 31 October 2025 for AY 2025-26, "
         "unless extended by CBDT. Transfer-pricing cases (Form 3CEB) get until 30 November.",
         [{"source": "Income-tax Act, s.44AB", "ref": "Tax audit due date"},
          {"source": "s.139(1)", "ref": "Return filing due dates"}],
         "openrouter/auditmind", 640, 880.0),
    ]
    for (client_id, asked_by, qtype, question, response, sources, model, tokens, latency) in rows:
        db.add(Query(
            client_id=client_id,
            asked_by=asked_by,
            question=question,
            response=response,
            sources_cited=sources,
            query_type=qtype,
            model_used=model,
            tokens_used=tokens,
            latency_ms=latency,
            resolved_at=NOW - timedelta(hours=3),
        ))


async def _seed_tax_intel(db) -> None:
    existing = await db.scalar(select(TaxIntel).limit(1))
    if existing:
        print("World Tax Radar already populated — skipping.")
        return
    items = [
        ("Budget 2026: NRI residency threshold under review for high-net-worth returnees",
         "The Finance Ministry is consulting on tightening the 'deemed resident' rule for NRIs with "
         "Indian-sourced income above ₹15L, effective AY 2027-28.",
         "https://example.gov.in/budget-2026-nri", "India", "Residency", 95,
         ["NRI", "deemed resident", "Budget 2026"]),
        ("India-USA DTAA: updated guidance on foreign tax credit timing",
         "CBDT clarifies that FTC under Rule 128 may be claimed in the year the foreign income is "
         "offered to tax in India, easing mismatches for US-based NRIs.",
         "https://example.gov.in/cbdt-ftc-guidance", "India-USA", "DTAA", 88,
         ["DTAA", "FTC", "Rule 128", "Form 67"]),
        ("UAE corporate tax: impact on Indian-origin business owners",
         "The UAE's 9% corporate tax interacts with India-UAE DTAA for NRIs running mainland "
         "entities; permanent-establishment exposure should be reviewed.",
         "https://example.ae/uae-ct-india", "UAE", "Corporate Tax", 72,
         ["UAE", "corporate tax", "PE", "DTAA"]),
        ("GST: new ITC reconciliation rules for FY2026-27",
         "Auto-population of GSTR-2B tightens; ITC mismatches beyond ₹50k now auto-flag an ASMT-10.",
         "https://example.gov.in/gst-itc-2026", "India", "GST", 60,
         ["GST", "ITC", "GSTR-2B", "ASMT-10"]),
        ("FEMA: repatriation limits for NRO accounts revised",
         "RBI revises the USD 1M per financial year repatriation framework documentation for NRO "
         "balances; CA certification (Form 15CB) requirements clarified.",
         "https://example.rbi.org.in/fema-nro", "India", "FEMA", 84,
         ["FEMA", "NRO", "repatriation", "15CA-CB"]),
        ("OECD Pillar Two: India's implementation timeline",
         "India signals adoption of the 15% global minimum tax for in-scope MNE groups, with "
         "domestic top-up rules expected in the next Finance Act.",
         "https://example.oecd.org/pillar-two-india", "Global", "BEPS", 55,
         ["OECD", "Pillar Two", "GloBE", "minimum tax"]),
    ]
    for (title, summary, url, juris, topic, score, terms) in items:
        db.add(TaxIntel(
            title=title,
            summary=summary,
            source_url=url,
            published_at=NOW - timedelta(days=2),
            jurisdiction=juris,
            topic=topic,
            nri_impact_score=score,
            matched_terms=terms,
        ))


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_create(db, model, match: dict, defaults: dict, created_flag: bool = False):
    """Return an existing row matching `match`, else create one from `match | defaults`."""
    stmt = select(model)
    for k, v in match.items():
        stmt = stmt.where(getattr(model, k) == v)
    obj = await db.scalar(stmt)
    if obj is not None:
        if created_flag:
            obj._seed_created = False
        return obj
    obj = model(**{**match, **defaults})
    db.add(obj)
    if created_flag:
        obj._seed_created = True
    label = match.get("email") or match.get("pan") or match.get("slug") or model.__name__
    print(f"  + created {model.__name__}: {label}")
    return obj


async def _ensure_schema() -> None:
    """Create the pgvector extension and all tables (fresh-DB convenience; skips Alembic)."""
    async with engine.begin() as conn:
        await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    print("Schema ensured (pgvector + tables).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OperatorOS demo data.")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create tables on a fresh DB before seeding (skips Alembic; demo use only).",
    )
    args = parser.parse_args()

    async def _run() -> None:
        if args.create_tables:
            await _ensure_schema()
        await seed()
        await engine.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
