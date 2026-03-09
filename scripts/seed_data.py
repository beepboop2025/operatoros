#!/usr/bin/env python3
"""
seed_data.py - Create initial admin user and sample client data for OperatorOS.

Usage:
    python scripts/seed_data.py

Reads DATABASE_URL from the environment (or .env file).
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import asyncpg  # noqa: E402
from passlib.context import CryptContext  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://operatoros:operatoros@localhost:5432/operatoros",
)

# Strip the +asyncpg driver suffix so asyncpg raw connection works
DSN = DATABASE_URL.replace("+asyncpg", "")


# ── Seed Data ─────────────────────────────────────────────────────────────────

ADMIN_USER = {
    "id": str(uuid4()),
    "email": "admin@operatoros.local",
    "full_name": "System Administrator",
    "hashed_password": pwd_context.hash("admin123!"),
    "role": "admin",
    "is_active": True,
}

SAMPLE_CLIENTS = [
    {
        "id": str(uuid4()),
        "name": "Acme Corporation",
        "email": "contact@acme.example.com",
        "phone": "+1-555-0100",
        "company": "Acme Corp",
        "status": "active",
        "notes": "Enterprise client, onboarded Q1 2024.",
    },
    {
        "id": str(uuid4()),
        "name": "Globex Industries",
        "email": "info@globex.example.com",
        "phone": "+1-555-0200",
        "company": "Globex Industries",
        "status": "active",
        "notes": "Mid-market account, monthly retainer.",
    },
    {
        "id": str(uuid4()),
        "name": "Initech Solutions",
        "email": "hello@initech.example.com",
        "phone": "+1-555-0300",
        "company": "Initech Solutions",
        "status": "lead",
        "notes": "Prospect from trade show, follow up next week.",
    },
    {
        "id": str(uuid4()),
        "name": "Umbrella Holdings",
        "email": "ops@umbrella.example.com",
        "phone": "+1-555-0400",
        "company": "Umbrella Holdings",
        "status": "active",
        "notes": "Key account, custom SLA in place.",
    },
    {
        "id": str(uuid4()),
        "name": "Stark Ventures",
        "email": "tony@stark.example.com",
        "phone": "+1-555-0500",
        "company": "Stark Ventures",
        "status": "lead",
        "notes": "High-value prospect, demo scheduled.",
    },
]


async def seed() -> None:
    print(f"Connecting to: {DSN.split('@')[-1]}")
    conn = await asyncpg.connect(DSN)

    try:
        # ── Ensure pgvector extension ─────────────────────────────────────
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("pgvector extension ensured.")

        # ── Create users table if not exists ──────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          UUID PRIMARY KEY,
                email       VARCHAR(255) UNIQUE NOT NULL,
                full_name   VARCHAR(255) NOT NULL,
                hashed_password TEXT NOT NULL,
                role        VARCHAR(50) NOT NULL DEFAULT 'user',
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # ── Create clients table if not exists ────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id          UUID PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                email       VARCHAR(255),
                phone       VARCHAR(50),
                company     VARCHAR(255),
                status      VARCHAR(50) NOT NULL DEFAULT 'lead',
                notes       TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # ── Insert admin user ─────────────────────────────────────────────
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1", ADMIN_USER["email"]
        )
        if existing:
            print(f"Admin user already exists: {ADMIN_USER['email']}")
        else:
            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO users (id, email, full_name, hashed_password, role, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                ADMIN_USER["id"],
                ADMIN_USER["email"],
                ADMIN_USER["full_name"],
                ADMIN_USER["hashed_password"],
                ADMIN_USER["role"],
                ADMIN_USER["is_active"],
                now,
                now,
            )
            print(f"Created admin user: {ADMIN_USER['email']} (password: admin123!)")

        # ── Insert sample clients ─────────────────────────────────────────
        inserted = 0
        for client in SAMPLE_CLIENTS:
            existing = await conn.fetchval(
                "SELECT id FROM clients WHERE email = $1", client["email"]
            )
            if existing:
                print(f"  Client already exists: {client['name']}")
                continue

            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO clients (id, name, email, phone, company, status, notes, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                client["id"],
                client["name"],
                client["email"],
                client["phone"],
                client["company"],
                client["status"],
                client["notes"],
                now,
                now,
            )
            inserted += 1
            print(f"  Created client: {client['name']} ({client['status']})")

        print(f"\nSeed complete: 1 admin user, {inserted} new clients inserted.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
