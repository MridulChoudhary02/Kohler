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
| LLM Layer | LiteLLM → Groq (openai/gpt-oss-120b, free tier) | High-speed inference, no cost dependency. |

---

## Project Structure

```
Kohler/
├── PRD_Kohler_Track2_Hospital.md       # Full product spec (authoritative)
├── PROMPT_LOG_PROTOCOL.md              # Agent logging protocol
├── PROMPT_LOG.md                       # Build log (append-only, per protocol)
├── docker-compose.yml                  # Local dev: PostgreSQL + backend
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                   # Schema migrations
│   ├── app/
│   │   ├── main.py                     # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py               # Settings (pydantic-settings)
│   │   │   └── database.py             # Async engine + session
│   │   ├── models/
│   │   │   └── models.py               # All ORM models (Section 6 ER)
│   │   ├── api/                        # API v1 routers
│   │   └── services/                   # App-layer wrappers (not detection engine):
│   │       ├── detection_service.py
│   │       ├── ticket_service.py
│   │       ├── llm_service.py
│   │       ├── investigation_service.py
│   │       ├── fixture_health_service.py
│   │       └── sustainability_service.py
│   ├── detection/                      # Core detection engine:
│   │   ├── baseline.py                 # 30-day baseline computation & EWMA
│   │   ├── state.py                    # Fixture state machine & tracker
│   │   ├── engine.py                   # Anomaly detection core
│   │   ├── runner.py                   # Stream processor & batch runner
│   │   ├── sensor_health.py            # Sensor health & telemetry quality
│   │   ├── hygiene.py                  # Hygiene stagnation & breach prediction
│   │   ├── trend_detector.py           # Trend & wear degradation detection
│   │   └── tests/                      # Detection test suite
│   ├── simulator/                      # Telemetry generator:
│   │   ├── profiles.py                 # Usage profiles & fixture specs
│   │   ├── anomaly.py                  # Anomaly injection logic
│   │   ├── engine.py                   # Simulator engine
│   │   ├── runner.py                   # Telemetry generation runner
│   │   ├── burst.py                    # Burst patterns & events
│   │   ├── scoring.py                  # Scoring & evaluation metrics
│   │   ├── test_scenarios.py           # Test scenarios definition
│   │   └── generate_test_set.py        # 3-day test set generator
│   └── scripts/
│       ├── seed_data.py                # Hospital seed data definition
│       ├── seed.py                     # Seed runner
│       ├── replay_simulator_to_api.py  # Ingest simulator output into API
│       └── reset_clean_state.py        # Database reset utility
│
└── frontend/                           # Next.js 14 Dashboard
    └── src/
        ├── app/                        # Page structure:
        │   ├── page.tsx                # Overview
        │   ├── tickets/page.tsx        # Tickets Kanban & dispatch
        │   ├── fixtures/health/page.tsx# Fixture health & sensor status
        │   ├── sustainability/page.tsx # Water/energy sustainability analytics
        │   └── chat/page.tsx           # AI facility assistant & natural language query
        └── components/                 # UI components:
            ├── FixtureHealthDetailModal.tsx
            ├── FixtureDrillDownModal.tsx
            ├── CompactAlertsList.tsx
            └── Header.tsx
```

---

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.12+ (for local dev without Docker)
- Node.js 18+ and npm

> [!NOTE]
> `GROQ_API_KEY` must be set in `backend/.env` for the LLM investigator and chat features to work (get a free key from Groq).

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
# Edit .env and set GROQ_API_KEY for LLM features
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
cd backend
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 6. Generate Telemetry and Ingest

Run the simulator to produce sample telemetry, then ingest it into the live API:

```bash
cd backend
# Generate the 3-day canonical test dataset
python -m simulator.generate_test_set

# Ingest/replay simulator output into the live API
python scripts/replay_simulator_to_api.py --telemetry simulator/output/test_set/combined_telemetry.jsonl
```

### 7. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard runs on http://localhost:3000
```

---

## Delivery Phases

| Phase | Goal | Status |
|---|---|---|
| **Phase 0** | Repo scaffold, schema, seed data | ✅ Complete |
| Phase 1 | Telemetry Simulator | ✅ Complete |
| Phase 2 | Detection Engine Core | ✅ Complete |
| Phase 3 | Sensor Health + Hygiene Prediction | ✅ Complete |
| Phase 4 | Persistence + API Layer | ✅ Complete |
| Phase 5 | Ticket Dispatch Engine | ✅ Complete |
| Phase 6 | Dashboard | ✅ Complete |
| Phase 7 | LLM Layer | ✅ Complete |
| Phase 8 | Validation, Polish, Demo Assets | ✅ Complete |

---

## Documentation

- `PROMPT_LOG.md` — agent build log (converted to submission's Prompts Documentation PDF in Phase 8)
- `PRD_Kohler_Track2_Hospital.md` — authoritative product spec; all implementation must match it
## Demo Video
Walkthrough video: <https://drive.google.com/file/d/1WGbEjOZqYK4qxu0xKR3wljCmOcdpofhE/view?usp=sharing>
