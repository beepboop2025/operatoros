<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React_18-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/n8n-EA4B71?style=for-the-badge&logo=n8n&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
</p>

<h1 align="center">OperatorOS / AuditMind</h1>

<p align="center">
  <strong>AI-Powered Operations Platform for Chartered Accountancy & Tax Advisory Firms</strong>
</p>

<p align="center">
  Built for the Indian tax ecosystem &mdash; Income Tax Act, GST, Companies Act, FEMA, and 50+ compliance frameworks.<br/>
  The firm's second brain that handles tax computation, compliance tracking, document intelligence, and client management.
</p>

---

## The Problem

Indian CA firms juggle hundreds of clients, thousands of deadlines, and constantly changing tax law. Most still operate on Excel sheets, WhatsApp groups, and manual follow-ups. A single missed deadline means penalties. A single wrong computation means client trust lost.

**OperatorOS replaces that chaos with a unified intelligence layer.**

---

## What It Does

### Tax Computation Engine

The core of the platform. Accurate Indian tax calculations using `Decimal` arithmetic (no floating-point surprises on financial data).

| Calculator | What It Computes |
|-----------|-----------------|
| **Income Tax** | Old vs New regime side-by-side comparison with slab breakdown, 87A rebate, surcharge, cess. Supports AY 2025-26 and AY 2026-27 (Budget 2025 slabs). |
| **TDS** | 18 sections covered (192, 194A, 194C, 194H, 194I, 194J, 194Q, etc.) with PAN/no-PAN rates and threshold checks. |
| **GST** | Intra-state (CGST+SGST) vs inter-state (IGST) split, HSN/SAC lookup, rate determination. |
| **Capital Gains** | LTCG/STCG classification, CII indexation (2001-2026), holding period rules, dual computation for pre-July 2024 assets (20% with indexation vs 12.5% without). |
| **Interest** | Section 234A (late filing), 234B (advance tax shortfall), 234C (deferment) with month-wise breakdown. |
| **HRA** | Section 10(13A) exemption with metro/non-metro distinction and three-way minimum calculation. |
| **Depreciation** | WDV method with IT Act rates, half-year rule, additional depreciation for manufacturing. |

### Compliance Calendar

Auto-generates and tracks every deadline for every client:

- TDS returns (quarterly) &mdash; 24Q, 26Q, 27Q, 27EQ
- Advance tax installments &mdash; Jun 15, Sep 15, Dec 15, Mar 15
- GST returns &mdash; GSTR-1, GSTR-3B, GSTR-9, GSTR-9C
- ITR filing &mdash; Jul 31 (non-audit), Oct 31 (audit), Nov 30 (transfer pricing)
- ROC filings &mdash; AOC-4, MGT-7, DIR-3 KYC, DPT-3
- Tax audit (Sep 30), LLP forms, and more

Color-coded urgency. Automated reminders 15 days before. Escalation 5 days before. Penalty calculation if missed.

### AI Query Engine (RAG Pipeline)

Ask tax questions in natural language. The system:

1. Classifies the query (factual / computation / advisory / procedural)
2. Searches your document database via pgvector semantic search
3. Retrieves relevant client history and tax provisions
4. Generates a cited, structured response via OpenRouter LLM
5. Flags action items and deadlines

Built-in knowledge base: **50 commonly referenced tax sections** and **21 recent CBDT/CBIC circulars**.

### Document Intelligence

Upload documents (PDF, images, scans) and the system:

- Extracts text via PyPDF2 / Tesseract OCR
- Parses structured data (Form 26AS entries, GST notice demands, bank statement transactions)
- Generates summaries with action items
- Creates vector embeddings for future semantic search
- Routes to the right team member

### Notice Management

When a tax notice arrives:

- Classifies notice type (143(1), 148, 142(1), DRC-01, etc.)
- Extracts demand amount, sections cited, response deadline
- Assesses urgency (critical / high / medium / low)
- Generates draft response with legal citations
- Tracks through to resolution

### Communication Drafting

AI-powered drafting for:

- Client advisories (Budget impact, regulatory changes)
- Notice responses (formal, citation-heavy)
- Engagement letters (ICAI SQC-1 compliant)
- Board resolutions, management representation letters

### Workflow Automation (n8n)

Five pre-built workflows:

| Workflow | Trigger | What It Does |
|----------|---------|-------------|
| Client Onboarding | Webhook | Create client, generate compliance calendar, send welcome email |
| Monthly GST Cycle | Cron (1st of month) | Remind all clients of GSTR-1 (11th) and GSTR-3B (20th) deadlines |
| ITR Filing Pipeline | Webhook | Compute tax both regimes, email comparison to client, update task status |
| Notice Response | Webhook | Fetch notice, generate draft, route to CA for review |
| TDS Compliance | Cron (quarterly) | Send reminders, escalate overdue TDS returns with penalty warnings |

---

## Architecture

```
                                    +-----------+
                                    |   Caddy   |  (reverse proxy + TLS)
                                    +-----+-----+
                                          |
                    +--------------------+--------------------+
                    |                    |                    |
              +-----+-----+      +------+------+      +-----+-----+
              |  Frontend  |      |   FastAPI   |      |    n8n    |
              |  React 18  |      |   Backend   |      | Workflows |
              | TypeScript |      |   Python    |      |           |
              +-----+------+      +------+------+      +-----+-----+
                    |                    |                    |
                    +--------------------+--------------------+
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
              +-----+-----+      +------+------+      +-----+-----+
              | PostgreSQL |      |    Redis    |      | OpenRouter |
              |  pgvector  |      |   Cache +   |      |  LLM API   |
              |            |      | Rate Limit  |      |            |
              +------------+      +-------------+      +------------+
```

### Backend Stack

| Component | Purpose |
|-----------|---------|
| **FastAPI** | Async API framework with auto-generated OpenAPI docs |
| **SQLAlchemy 2.0** | Async ORM with `Mapped[]` type annotations |
| **pgvector** | Vector similarity search for document embeddings |
| **Redis** | Caching, rate limiting (sliding window), embedding cache |
| **OpenRouter** | LLM routing &mdash; Haiku for fast lookups, Sonnet for deep reasoning |
| **Alembic** | Database migrations |
| **PyPDF2 + Tesseract** | Document text extraction (PDF + OCR) |

### Frontend Stack

| Component | Purpose |
|-----------|---------|
| **React 18** | UI framework |
| **TypeScript** | Strict type safety across 40+ API interfaces |
| **Vite 5** | Build tool with code splitting (vendor/charts/query chunks) |
| **Tailwind CSS v4** | Utility-first styling |
| **TanStack Query** | Server state management with caching |
| **Recharts** | Dashboard visualizations |
| **Lucide React** | Icon system |

---

## Project Structure

```
operatoros/
├── backend/
│   ├── app/
│   │   ├── models/          # 8 SQLAlchemy models (User, Client, Document, Query, ...)
│   │   ├── schemas/         # 47 Pydantic v2 schemas with validators
│   │   ├── routes/          # 10 route modules, 46 API endpoints
│   │   ├── services/        # Tax engine, RAG, document processor, OpenRouter, ...
│   │   ├── middleware/       # JWT auth, rate limiting, audit logging
│   │   ├── utils/           # Tax constants, CII table, TDS/GST rates, compliance calendar
│   │   └── knowledge/       # 50 tax sections + 21 circulars reference data
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/      # 10 React components (Dashboard, TaxComputer, QueryChat, ...)
│       ├── api/             # Typed API client with 40+ interfaces
│       ├── hooks/           # Auth context + hook
│       └── utils/           # Indian number formatting, date formatting
├── n8n/workflows/           # 5 automation workflow templates
├── scripts/                 # Backup, seed data
├── docker-compose.yml       # Development stack
├── docker-compose.prod.yml  # Production overrides
└── Caddyfile                # Reverse proxy config
```

**By the numbers:** 75+ source files, ~18,400 lines of code, 46 API endpoints, 8 database models, 7 computation engines, 5 n8n workflows.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- An [OpenRouter](https://openrouter.ai/) API key (for AI features)

### Quick Start

```bash
# Clone
git clone https://github.com/beepboop2025/operatoros.git
cd operatoros

# Configure
cp .env.example .env
# Edit .env and set your OPENROUTER_API_KEY

# Launch
docker compose up -d

# Initialize database
docker compose exec fastapi alembic upgrade head

# Seed admin user + sample data
docker compose exec fastapi python scripts/seed_data.py
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| API (Swagger UI) | http://localhost:8000/docs | JWT Bearer Token |
| Frontend | http://localhost:5173 | `admin@operatoros.local` / `admin123!` |
| n8n Workflows | http://localhost:5678 | Set up on first visit |

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # Dev server with hot reload at :5173
npm run typecheck    # TypeScript type checking only
npm run build        # Production build (type-check + bundle)
```

### Backend Development

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## API Overview

All endpoints are authenticated via JWT Bearer tokens. Role-based access control (admin, partner, associate, client_view).

### Core Endpoints

```
POST   /api/auth/login                  Login, get JWT token
POST   /api/auth/register               Create user (admin only)

GET    /api/clients                     List clients (paginated, searchable)
POST   /api/clients                     Create client
GET    /api/clients/{id}/calendar       Client compliance calendar

POST   /api/compute/tax                 Income tax — old vs new regime
POST   /api/compute/tds                 TDS calculation
POST   /api/compute/gst                 GST liability
POST   /api/compute/capital-gains       Capital gains with indexation
POST   /api/compute/interest            Interest u/s 234A/B/C
POST   /api/compute/hra                 HRA exemption
POST   /api/compute/depreciation        Depreciation schedule

POST   /api/queries                     Ask a tax question (RAG)
POST   /api/documents/upload            Upload & process document
POST   /api/documents/search            Semantic search

GET    /api/compliance/tasks            List compliance tasks
GET    /api/compliance/overdue          All overdue tasks
POST   /api/compliance/generate         Generate compliance calendar

POST   /api/notices/process             Process a tax notice
POST   /api/notices/{id}/draft-response Draft response

POST   /api/draft/advisory              Client advisory letter
POST   /api/draft/engagement-letter     Engagement letter

GET    /api/dashboard/stats             Firm-wide metrics
POST   /api/workflow/trigger            Trigger n8n workflow
```

Full interactive documentation available at `/docs` (Swagger UI) when the server is running.

---

## Database Schema

8 tables with pgvector extension for semantic search:

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | Team members | email, role (admin/partner/associate/client_view), hashed_password |
| `clients` | Client entities | PAN, GSTIN, CIN, entity_type, assigned_to |
| `documents` | Uploaded documents | doc_type, parsed_json, summary, `vector(1536)` embedding |
| `queries` | AI query log | question, response, sources_cited, model_used, tokens_used |
| `compliance_tasks` | Deadline tracking | task_type, due_date, status, assessment_year |
| `tax_computations` | Computation audit trail | regime, gross_income, deductions, tax_liability, full working |
| `notices` | Tax/GST notices | notice_type, response_deadline, status, response_draft |
| `audit_logs` | Activity tracking | user, action, entity, details, IP address |

Row-level security enforced. All client-scoped queries filtered by client_id.

---

## Production Deployment

### With Docker Compose + Caddy

```bash
# Update .env with production values
# Update Caddyfile with your domain

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Caddy auto-provisions TLS certificates. Production config includes:
- 4 Uvicorn workers (no hot-reload)
- CPU/memory resource limits
- Health checks on all services
- Caddy security headers

### Recommended Infra

- **VPS**: Hetzner CX31 or DigitalOcean $24/mo (4 vCPU, 8 GB RAM)
- **Database**: Managed PostgreSQL or self-hosted with nightly backups
- **Backups**: `scripts/backup.sh` dumps PostgreSQL and uploads to S3

```bash
# Automated nightly backup (add to crontab)
0 2 * * * /path/to/operatoros/scripts/backup.sh
```

---

## Tax Knowledge Coverage

### Direct Taxes
- Income Tax Act, 1961 &mdash; all major sections and schedules
- Old Regime vs New Regime (AY 2025-26 & AY 2026-27 with Budget 2025 changes)
- TDS/TCS provisions (Sections 192&ndash;206C) with rates, thresholds, and due dates
- Capital gains &mdash; CII indexation, exemptions (54, 54EC, 54F), holding period rules
- Presumptive taxation (44AD, 44ADA, 44AE)
- Interest calculations (234A/B/C) and penalties (234F, 271B)

### Indirect Taxes
- GST (CGST, SGST, IGST) &mdash; registration, returns, ITC, reverse charge
- HSN/SAC classification with rate lookup
- E-invoicing and e-way bill provisions

### Corporate Compliance
- Companies Act, 2013 &mdash; AOC-4, MGT-7, DIR-3 KYC, DPT-3
- LLP Act &mdash; Form 8, Form 11
- ROC filing calendar

### Built-in Reference Data
- Cost Inflation Index: FY 2001-02 to FY 2025-26
- TDS rate table: 18 sections with thresholds and PAN/no-PAN rates
- GST rate table: 40+ common goods/services with HSN/SAC codes
- 50 commonly referenced tax sections with key points
- 21 recent CBDT/CBIC circulars

---

## Security

- JWT authentication with bcrypt password hashing
- Role-based access control (4 roles with endpoint-level enforcement)
- Redis sliding-window rate limiting (30/60/120 requests per minute by endpoint category)
- Audit logging on all write operations (who did what, when, from where)
- Input validation via Pydantic (PAN, GSTIN, CIN regex validators)
- CORS configuration with explicit origin allowlist
- Environment variable configuration (secrets never in code)
- `.env.example` provided, `.env` in `.gitignore`

---

## Roadmap

- [ ] WhatsApp integration for client reminders (Twilio/WhatsApp Business API)
- [ ] Bulk TDS return preparation (24Q/26Q/27Q generation)
- [ ] Form 26AS / AIS auto-reconciliation
- [ ] Multi-tenant architecture for managing multiple firms
- [ ] Mobile app (React Native)
- [ ] Stripe/Razorpay billing for SaaS model
- [ ] Client self-service portal

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | React 18, TypeScript (strict), Vite 5, Tailwind CSS v4 |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| AI/LLM | OpenRouter (Claude Sonnet / Haiku) |
| Search | pgvector cosine similarity (1536-dim embeddings) |
| Workflows | n8n (self-hosted) |
| Proxy | Caddy (auto TLS) |
| Containers | Docker Compose |

---

## License

Private. All rights reserved.

---

<p align="center">
  <strong>Built by mrinal</strong>
</p>
