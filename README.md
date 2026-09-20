# Kohler Smart Facility & Sustainability Manager — Hospital Edition

> **Track 2 — KOHLER-MITWPU AI Research Lab Program**

A hospital-grade facility intelligence platform that ingests fixture-level telemetry, detects leaks with statistical confidence, predicts hygiene threshold breaches before they occur, and routes explainable maintenance tickets to the right team at the right priority.

---

## Architecture

```
[Telemetry Simulator] → [Ingestion API] → [Detection Engine] → [Event Store]
                                                    ↓
                                          [Ticket Dispatch Engine] → [Ticket Store]
                                                    ↓
                              [Dashboard (Next.js)]  ←  [Query/API layer]  →  [LLM Layer]
```

**Stack:**
| Layer | Technology | Reason |
|---|---|---|
| Backend | Python + FastAPI | Async-native; rich scientific ecosystem for EWMA/UCL |
| Database | PostgreSQL 16 | Time-series friendly, strong relational model, JSONB |
| ORM | SQLAlchemy 2.0 (async) | Maps cleanly to ER diagram; Alembic auto-migrations |
| Migrations | Alembic | Canonical FastAPI/SQLAlchemy migration tool |
| Frontend | Next.js 14 + TypeScript | SSR dashboard; great chart library ecosystem |
| LLM Layer | LiteLLM → GPT-4o | Provider-agnostic; swap model with one env-var |

---

## Project Structure

```
Kohler/
├── PRD_Kohler_Track2_Hospital.md   # Full product spec (authoritative)
├── PROMPT_LOG_PROTOCOL.md          # Agent logging protocol
├── PROMPT_LOG.md                   # Build log (append-only, per protocol)
├── docker-compose.yml              # Local dev: PostgreSQL + backend
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py   ← Phase 0 migration
│   ├── app/
│   │   ├── main.py                      ← FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py                ← Settings (pydantic-settings)
│   │   │   └── database.py              ← Async engine + session
│   │   ├── models/
│   │   │   └── models.py                ← All ORM models (Section 6 ER)
│   │   ├── api/                         ← Phase 4+ routers
│   │   └── services/                    ← Phase 2/3 detection engine
│   └── scripts/
│       ├── seed_data.py                 ← Hospital seed data definition
│       └── seed.py                      ← Seed runner
│
└── frontend/                            ← Phase 6 (Next.js)
```

---

## Quick Start (Phase 0)

### Prerequisites
- Docker Desktop
- Python 3.12+ (for local dev without Docker)

### 1. Start PostgreSQL

```bash
docker-compose up postgres -d
```

### 2. Set up backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Run migrations

```bash
cd backend
alembic upgrade head
```

### 4. Seed data

```bash
cd backend
python scripts/seed.py
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

---

## Delivery Phases

| Phase | Goal | Status |
|---|---|---|
| **Phase 0** | Repo scaffold, schema, seed data | ✅ Complete |
| Phase 1 | Telemetry Simulator | ⏳ Pending |
| Phase 2 | Detection Engine Core | ⏳ Pending |
| Phase 3 | Sensor Health + Hygiene Prediction | ⏳ Pending |
| Phase 4 | Persistence + API Layer | ⏳ Pending |
| Phase 5 | Ticket Dispatch Engine | ⏳ Pending |
| Phase 6 | Dashboard | ⏳ Pending |
| Phase 7 | LLM Layer | ⏳ Pending |
| Phase 8 | Validation, Polish, Demo Assets | ⏳ Pending |

---

## Documentation

- `PROMPT_LOG.md` — agent build log (converted to submission's Prompts Documentation PDF in Phase 8)
- `PRD_Kohler_Track2_Hospital.md` — authoritative product spec; all implementation must match it
## Demo Video
Walkthrough video: <https://drive.google.com/file/d/1WGbEjOZqYK4qxu0xKR3wljCmOcdpofhE/view?usp=sharing>
