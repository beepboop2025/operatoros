# OperatorOS

**AI-powered tax advisory and compliance platform for Indian chartered accountancy firms.**

OperatorOS (also known as AuditMind) is a full-stack intelligence platform that automates tax computation, compliance tracking, document processing, and client management for CA firms operating under the Indian tax ecosystem. It combines a precision tax engine with RAG-based AI to handle everything from Income Tax and GST calculations to notice response drafting and deadline management.

---

## Features

### Tax Computation Engine

- **Income Tax** -- Old vs New regime comparison with slab breakdown, Section 87A rebate, surcharge, and cess (AY 2025-26 and AY 2026-27)
- **TDS** -- 18 sections (192, 194A, 194C, 194H, 194I, 194J, 194Q, and others) with PAN/no-PAN rates and threshold checks
- **GST** -- Intra-state (CGST+SGST) and inter-state (IGST) split with HSN/SAC lookup
- **Capital Gains** -- LTCG/STCG classification, CII indexation (2001-2026), holding period rules, dual computation for pre-July 2024 assets
- **Interest** -- Sections 234A, 234B, and 234C with month-wise breakdown
- **HRA** -- Section 10(13A) exemption with metro/non-metro distinction
- **Depreciation** -- WDV method with IT Act rates, half-year rule, and additional depreciation for manufacturing

### AI Query Engine (RAG Pipeline)

- Natural language tax queries with classified intent (factual, computation, advisory, procedural)
- Semantic search over uploaded documents via pgvector embeddings
- Cited, structured responses generated through OpenRouter LLM
- Built-in knowledge base: 50 tax sections, 21 CBDT/CBIC circulars, CII table, TDS/TCS rates, GST rates

### Document Intelligence

- PDF text extraction (PyPDF2) and image OCR (Tesseract)
- Structured data parsing for Form 26AS, GST notices, and bank statements
- Automatic summary generation with action items
- Vector embeddings for semantic search

### Compliance Calendar

- Auto-generated deadlines per client: TDS returns, advance tax, GST returns, ITR filing, ROC filings
- Color-coded urgency with automated reminders (15 days) and escalation (5 days)
- Penalty calculation for missed deadlines

### Notice Management

- Classification of notice type (143(1), 148, 142(1), DRC-01, and others)
- Extraction of demand amount, cited sections, and response deadline
- AI-drafted responses with legal citations

### Communication Drafting

- Client advisories, notice responses, engagement letters, and board resolutions
- ICAI SQC-1 compliant templates

### Workflow Automation

Five pre-built n8n workflows: client onboarding, monthly GST cycle, ITR filing pipeline, notice response, and TDS compliance.

---

## Tech Stack

| Layer | Technology |
|------------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS v4, TanStack Query |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache** | Redis 7 |
| **AI/LLM** | OpenRouter (Claude Sonnet / Haiku) |
| **Search** | pgvector cosine similarity (1536-dim embeddings) |
| **Workflows** | n8n (self-hosted) |
| **Proxy** | Caddy (automatic TLS) |
| **Containers** | Docker Compose |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An [OpenRouter](https://openrouter.ai/) API key (required for AI features)

### Installation

```bash
# Clone the repository
git clone https://github.com/beepboop2025/operatoros.git
cd operatoros

# Create environment file
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# Start all services
docker compose up -d

# Run database migrations
docker compose exec fastapi alembic upgrade head

# Seed the admin user and sample data
docker compose exec fastapi python scripts/seed_data.py
```

### Access Points

| Service | URL |
|---------|-----|
| API (Swagger UI) | `http://localhost:8000/docs` |
| Frontend | `http://localhost:5173` |
| n8n Workflows | `http://localhost:5678` |

Default credentials: `admin@operatoros.local` / `admin123!`

### Production Deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production config includes Caddy with automatic TLS, 4 Uvicorn workers, resource limits, and health checks on all services.

---

## Architecture

Requests arrive through Caddy (reverse proxy with automatic TLS) and are routed to three services: the React frontend (served via Vite), the FastAPI backend, and the n8n workflow engine. The backend connects to PostgreSQL with the pgvector extension for structured data and semantic search, Redis for caching and rate limiting, and OpenRouter for LLM inference. The tax computation engine runs entirely server-side using Decimal arithmetic. Document uploads are processed through a pipeline of text extraction, embedding generation, and structured parsing before being stored with their vector representations for future retrieval.

Authentication is handled via JWT tokens with bcrypt password hashing. Four roles (admin, partner, associate, client_view) enforce endpoint-level access control. All write operations are audit-logged.

---

## API Endpoints

All endpoints require JWT Bearer authentication. Role-based access control is enforced per endpoint.

| Module | Prefix | Description |
|--------|--------|-------------|
| **Auth** | `/api/auth` | Login, registration, token management |
| **Clients** | `/api/clients` | Client CRUD, compliance calendar per client |
| **Documents** | `/api/documents` | Upload, process, and semantic search over documents |
| **Queries** | `/api/queries` | Natural language tax queries via RAG pipeline |
| **Compliance** | `/api/compliance` | Task listing, overdue tracking, calendar generation |
| **Compute** | `/api/compute` | Tax, TDS, GST, capital gains, interest, HRA, depreciation |
| **Notices** | `/api/notices` | Notice processing and response drafting |
| **Draft** | `/api/draft` | Advisory letters and engagement letters |
| **Dashboard** | `/api/dashboard` | Firm-wide metrics and statistics |
| **Workflow** | `/api/workflow` | Trigger n8n automation workflows |

Full interactive documentation is available at `/docs` (Swagger UI) when the server is running.

---

## License

MIT

