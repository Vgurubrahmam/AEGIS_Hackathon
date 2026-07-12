"""
AEGIS — FastAPI Application Entry Point
Emergency response multi-agent pipeline backend.

Startup:
  cd Backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db.engine import create_tables, AsyncSessionLocal
from db.seed import run_seed
from services.vector_store import vector_store

# ── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aegis")

settings = get_settings()


# ── Application Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Create database tables
      2. Seed resources and historical incidents
      3. Initialize ChromaDB and seed historical incidents for RAG
    Shutdown:
      - Cleanup (if needed)
    """
    logger.info("=" * 60)
    logger.info("  AEGIS Backend Starting...")
    logger.info("=" * 60)

    # 1. Create DB tables
    await create_tables()
    logger.info("✅ Database tables created.")

    # 2. Seed data
    async with AsyncSessionLocal() as session:
        historical = await run_seed(session)
    logger.info("✅ Database seeded.")

    # 3. Initialize ChromaDB + seed historical incidents
    vector_store.initialize()
    if historical:
        vector_store.seed_incidents(historical)
    logger.info("✅ ChromaDB initialized and seeded.")

    # Log config status
    logger.info(f"   Groq API:      {'✅ configured' if settings.groq_configured else '❌ NOT configured'}")
    logger.info(f"   Twilio:        {'✅ configured' if settings.twilio_configured else '⚠️  log-only mode'}")
    logger.info(f"   Google Maps:   {'✅ configured' if settings.google_maps_configured else '⚠️  gazetteer only'}")
    logger.info(f"   LLM (fast):    {settings.llm_model_fast}")
    logger.info(f"   LLM (strong):  {settings.llm_model_strong}")
    logger.info(f"   Confidence:    {settings.confidence_threshold}")
    logger.info("=" * 60)
    logger.info("  AEGIS Ready — http://localhost:8000/docs")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("AEGIS Backend shutting down.")


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AEGIS",
    description="AI-Enhanced Governance & Intelligence System — Multi-agent emergency response pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for hackathon (dashboard connects from localhost:3000 or similar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ────────────────────────────────────────────────────────────

from routers.twilio_webhook import router as twilio_router
from routers.simulate import router as simulate_router
from routers.incidents import router as incidents_router
from routers.resources import router as resources_router
from routers.dispatches import router as dispatches_router
from routers.sitreps import router as sitreps_router
from routers.agent_logs import router as agent_logs_router
from routers.dashboard_actions import router as actions_router
from routers.ws import router as ws_router

app.include_router(twilio_router)
app.include_router(simulate_router)
app.include_router(incidents_router)
app.include_router(resources_router)
app.include_router(dispatches_router)
app.include_router(sitreps_router)
app.include_router(agent_logs_router)
app.include_router(actions_router)
app.include_router(ws_router)


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def health_check():
    """Health check / root endpoint."""
    return {
        "service": "AEGIS Backend",
        "status": "operational",
        "version": "1.0.0",
        "groq_configured": settings.groq_configured,
        "twilio_configured": settings.twilio_configured,
        "google_maps_configured": settings.google_maps_configured,
    }


@app.get("/api/status", tags=["health"])
async def api_status():
    """Detailed API status with all endpoint documentation."""
    return {
        "status": "operational",
        "endpoints": {
            "POST /api/simulate/sms": "Simulate inbound SMS (primary demo entry point)",
            "POST /api/twilio/webhook": "Twilio inbound SMS webhook",
            "GET /api/incidents": "List all incidents",
            "GET /api/incidents/{id}": "Get single incident",
            "GET /api/resources": "List all resources",
            "GET /api/dispatches": "List all dispatches",
            "GET /api/sitreps": "List all situation reports",
            "GET /api/sitreps/latest": "Get latest situation report",
            "GET /api/agent-logs": "List agent activity logs",
            "POST /api/actions/ack-dispatch/{id}": "Acknowledge dispatch (dashboard button)",
            "POST /api/actions/resolve-incident/{id}": "Resolve incident",
            "WS /ws": "WebSocket for live dashboard updates",
        },
    }
