# AEGIS Backend

**AI-Enhanced Governance & Intelligence System**
Multi-agent emergency response pipeline powered by FastAPI, Groq LLMs, and real-time WebSocket streaming.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Pipeline Flow](#pipeline-flow)
- [Agent Details](#agent-details)
- [WebSocket Events](#websocket-events)
- [Database Schema](#database-schema)
- [Testing](#testing)

---

## Overview

AEGIS is an AI-powered emergency response system that processes citizen SMS reports through a sequential multi-agent pipeline. Each incoming message is triaged, verified, geolocated, matched to the nearest available resource, dispatched via SMS, and summarized in a live Situation Report — all within seconds.

### Key Features

- **6 AI Agents** working in a sequential pipeline
- **Real-time WebSocket** push after every pipeline step
- **Hybrid Geocoding** — landmark gazetteer + Google Maps API fallback
- **RAG-based Verification** — ChromaDB + sentence-transformers for pattern matching
- **Twilio SMS Integration** — inbound webhook + outbound dispatch
- **Graceful Degradation** — every external dependency has a fallback mode

---

## Architecture

```
Citizens SMS ─→ Twilio Webhook ─→ Orchestrator Pipeline
                                       │
                    ┌──────────────────┼───────────────────────┐
                    ▼                  ▼                       ▼
              Triage Agent      Verification Agent      Geolocation Agent
              (Groq 8B)        (ChromaDB + Groq 70B)    (Groq 8B + Maps)
                    │                  │                       │
                    └──────────────────┼───────────────────────┘
                                       │
                    ┌──────────────────┼───────────────────────┐
                    ▼                  ▼                       ▼
            Resource Matching    Dispatch Agent          SitRep Agent
            (SQL + Haversine)    (Twilio SMS)           (Groq 70B)
                    │                  │                       │
                    └──────────────────┼───────────────────────┘
                                       │
                                       ▼
                              WebSocket Broadcast ─→ Dashboard
```

---

## Tech Stack

| Component          | Technology                                     |
| ------------------ | ---------------------------------------------- |
| **Framework**      | FastAPI (async Python)                         |
| **LLM Provider**   | Groq API (Llama 3.1 8B + Llama 3.3 70B)       |
| **Vector Store**   | ChromaDB (local, persistent)                   |
| **Embeddings**     | sentence-transformers (`all-MiniLM-L6-v2`)     |
| **Database**       | SQLite via SQLAlchemy (async, aiosqlite)        |
| **SMS Gateway**    | Twilio (inbound webhook + outbound dispatch)   |
| **Geocoding**      | Landmark gazetteer + Google Maps Geocoding API |
| **Real-time**      | WebSocket (native FastAPI)                     |
| **Server**         | Uvicorn (ASGI)                                 |

---

## Project Structure

```
Backend/
├── main.py                     # FastAPI app entry point, lifespan, router mounting
├── config.py                   # Pydantic settings with .env loading
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
│
├── agents/                     # AI Agent implementations
│   ├── base.py                 # BaseAgent ABC with timing + error handling
│   ├── triage.py               # Severity + need_type classification (Groq 8B)
│   ├── verification.py         # RAG confidence scoring (ChromaDB + Groq 70B)
│   ├── geolocation.py          # Landmark extraction + geocoding (Groq 8B)
│   ├── resource_matching.py    # Nearest resource by haversine distance (no LLM)
│   ├── dispatch.py             # Outbound dispatch SMS via Twilio
│   └── sitrep.py               # Situation report generation (Groq 70B)
│
├── orchestrator/               # Pipeline controller
│   └── pipeline.py             # Sequential 7-step pipeline with decision gates
│
├── routers/                    # API route handlers
│   ├── twilio_webhook.py       # POST /api/twilio/webhook
│   ├── simulate.py             # POST /api/simulate/sms
│   ├── incidents.py            # GET /api/incidents
│   ├── resources.py            # GET /api/resources
│   ├── dispatches.py           # GET /api/dispatches
│   ├── sitreps.py              # GET /api/sitreps
│   ├── agent_logs.py           # GET /api/agent-logs
│   ├── dashboard_actions.py    # POST /api/actions/*
│   └── ws.py                   # WS /ws
│
├── services/                   # External service integrations
│   ├── llm_service.py          # Groq API wrapper with retry logic
│   ├── vector_store.py         # ChromaDB + sentence-transformers embeddings
│   ├── twilio_service.py       # Twilio SMS with log-only fallback
│   ├── geocoding_service.py    # Hybrid: landmark gazetteer + Google Maps
│   └── websocket_manager.py    # WebSocket connection manager + broadcast
│
├── db/                         # Database layer
│   ├── engine.py               # Async SQLAlchemy engine + session factory
│   ├── models.py               # ORM models (5 tables)
│   └── seed.py                 # Seeds 10 resources + 5 historical incidents
│
├── schemas/                    # Pydantic response models
│   ├── incident.py
│   ├── resource.py
│   ├── dispatch.py
│   ├── sitrep.py
│   ├── agent_log.py
│   └── websocket.py
│
└── utils/                      # Helper utilities
    ├── landmarks.py            # 35+ Hyderabad landmark coordinates
    └── haversine.py            # Distance calculation between coordinates
```

---

## Setup & Installation

### Prerequisites

- Python 3.11 or 3.12
- A [Groq API key](https://console.groq.com) (free tier available)
- (Optional) Twilio account for real SMS
- (Optional) Google Maps Geocoding API key

### Install Dependencies

```bash
cd Backend
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys (see [Environment Variables](#environment-variables)).

---

## Environment Variables

| Variable               | Required | Default                             | Description                                |
| ---------------------- | -------- | ----------------------------------- | ------------------------------------------ |
| `GROQ_API_KEY`         | **Yes**  | —                                   | Groq API key for LLM inference             |
| `TWILIO_ACCOUNT_SID`   | No       | —                                   | Twilio Account SID (dispatch SMS)          |
| `TWILIO_AUTH_TOKEN`     | No       | —                                   | Twilio Auth Token                          |
| `TWILIO_PHONE_NUMBER`  | No       | —                                   | Twilio phone number (sender)               |
| `GOOGLE_MAPS_API_KEY`  | No       | —                                   | Google Maps Geocoding API key              |
| `DATABASE_URL`         | No       | `sqlite+aiosqlite:///./aegis.db`    | SQLite database path                       |
| `CONFIDENCE_THRESHOLD` | No       | `0.6`                               | Below this → incident flagged for review   |
| `DEMO_CITY`            | No       | `Hyderabad`                         | City context for geocoding                 |

### Fallback Behavior

| Missing Key          | Fallback                                         |
| -------------------- | ------------------------------------------------ |
| Twilio credentials   | Dispatch SMS logged to console instead of sent   |
| Google Maps API key  | Geocoding uses landmark lookup table only        |
| Geolocation failure  | Falls back to city center coordinates            |

---

## Running the Server

```bash
# Start with auto-reload (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or explicitly with your Python version
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On startup, the server will:
1. Create SQLite database tables
2. Seed 10 emergency resources + 5 historical incidents
3. Initialize ChromaDB with sentence-transformers embeddings
4. Log configuration status (Groq ✅, Twilio ✅/⚠️, Google Maps ✅/⚠️)

**Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

### Ingestion

| Method | Endpoint                | Description                              |
| ------ | ----------------------- | ---------------------------------------- |
| POST   | `/api/twilio/webhook`   | Twilio inbound SMS webhook               |
| POST   | `/api/simulate/sms`     | Simulate SMS for demo/testing            |

### Data (Read-Only)

| Method | Endpoint                | Description                              |
| ------ | ----------------------- | ---------------------------------------- |
| GET    | `/api/incidents`        | List incidents (filter: `status`, `severity`) |
| GET    | `/api/incidents/{id}`   | Get single incident by ID                |
| GET    | `/api/resources`        | List resources (filter: `status`, `type`) |
| GET    | `/api/dispatches`       | List dispatch records                    |
| GET    | `/api/sitreps`          | List situation reports                   |
| GET    | `/api/sitreps/latest`   | Get latest situation report              |
| GET    | `/api/agent-logs`       | Agent activity logs (filter: `incident_id`, `agent_name`) |

### Dashboard Actions

| Method | Endpoint                              | Description                          |
| ------ | ------------------------------------- | ------------------------------------ |
| POST   | `/api/actions/ack-dispatch/{id}`      | Volunteer acknowledges dispatch      |
| POST   | `/api/actions/resolve-incident/{id}`  | Mark incident resolved (stores to ChromaDB) |

### Real-Time

| Method | Endpoint | Description                          |
| ------ | -------- | ------------------------------------ |
| WS     | `/ws`    | WebSocket for live dashboard updates |

### Health

| Method | Endpoint      | Description                |
| ------ | ------------- | -------------------------- |
| GET    | `/`           | Health check               |
| GET    | `/api/status` | Detailed API status        |

---

## Pipeline Flow

Each incident passes through **7 sequential steps** with decision gates:

```
Step 1: Create Incident          → status: new
Step 2: Triage Agent             → status: triaged        (severity + need_type)
Step 3: Verification Agent       → status: verified       (confidence score)
        ↳ Decision Gate          → status: needs_review   (if confidence < 0.6)
Step 4: Geolocation Agent        → status: located        (coordinates)
Step 5: Resource Matching Agent  → status: matched        (nearest resource)
Step 6: Dispatch Agent           → status: dispatched     (SMS sent)
Step 7: SitRep Agent             → generates situation report
```

### Decision Gate

After the Verification Agent, if the confidence score falls below the `CONFIDENCE_THRESHOLD` (default: `0.6`), the incident is flagged as `needs_review` and the pipeline **stops**. This prevents dispatching resources for unverified or suspicious reports.

---

## Agent Details

| Agent              | LLM Model                  | Purpose                                              |
| ------------------ | -------------------------- | ---------------------------------------------------- |
| **Triage**         | `llama-3.1-8b-instant`     | Classify severity (critical/high/medium) + need type (medical/rescue/food/shelter) |
| **Verification**   | `llama-3.3-70b-versatile`  | RAG-backed confidence scoring with heuristic flags   |
| **Geolocation**    | `llama-3.1-8b-instant`     | Extract landmark name → resolve coordinates          |
| **Resource Match** | None (SQL + haversine)     | Find nearest available resource by type + distance   |
| **Dispatch**       | None (Twilio API)          | Send dispatch SMS to volunteer/resource contact      |
| **SitRep**         | `llama-3.3-70b-versatile`  | Generate markdown situation report for EOC staff     |

---

## WebSocket Events

The dashboard connects to `ws://localhost:8000/ws` and receives JSON events:

| Event Type          | When                                      | Key Data Fields                               |
| ------------------- | ----------------------------------------- | --------------------------------------------- |
| `incident_created`  | New incident enters pipeline              | `incident_id`, `raw_text`, `sender_phone`     |
| `incident_updated`  | Incident state changes after each agent   | `status`, `severity`, `need_type`, `latitude`  |
| `agent_step`        | Each agent completes (6 per incident)     | `agent_name`, `step_status`, `reasoning`, `duration_ms` |
| `dispatch_created`  | Dispatch SMS sent                         | `dispatch_id`, `resource_name`, `contact_phone` |
| `sitrep_updated`    | New SitRep generated                      | `summary_text`, `incident_count`, `critical_count` |
| `dispatch_ack`      | Volunteer acknowledges dispatch           | `dispatch_id`, `status`                       |
| `incident_resolved` | Incident marked resolved                  | `status`                                      |

---

## Database Schema

### Tables

| Table          | Description                              |
| -------------- | ---------------------------------------- |
| `incidents`    | Emergency reports with status tracking   |
| `resources`    | Volunteers, vehicles, shelters           |
| `dispatches`   | SMS dispatch records                     |
| `sitreps`      | AI-generated situation reports           |
| `agent_logs`   | Step-by-step agent activity trace        |

### Incident Status Flow

```
new → triaged → verified → located → matched → dispatched → resolved
                    ↓
              needs_review
```

---

## Testing

### Simulate an Emergency SMS

```bash
curl -X POST http://localhost:8000/api/simulate/sms \
  -H "Content-Type: application/json" \
  -d '{"body": "Help, water rising near Charminar, family trapped on roof", "from_phone": "+911234567890"}'
```

### Query Results

```bash
# List all incidents
curl http://localhost:8000/api/incidents

# Check agent trace logs for an incident
curl "http://localhost:8000/api/agent-logs?incident_id=<INCIDENT_ID>"

# Get latest situation report
curl http://localhost:8000/api/sitreps/latest

# Check resource availability
curl http://localhost:8000/api/resources

# List dispatches
curl http://localhost:8000/api/dispatches
```

### Using Swagger UI

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for an interactive API explorer.

---

## License

Hackathon project — AEGIS Team.
