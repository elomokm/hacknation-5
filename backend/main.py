"""UNMAPPED API — FastAPI orchestrator.

Open infrastructure layer that closes the distance between informal skills
and economic opportunity in the age of AI.

Built for the World Bank Youth Summit × Hack-Nation 2026.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before importing modules that need ANTHROPIC_API_KEY
load_dotenv(Path(__file__).parent / ".env")

from api.middleware.error_handling import register_exception_handlers
from api.routes import (
    config_router,
    health_router,
    opportunity_router,
    profile_router,
    risk_router,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="UNMAPPED API",
    description=(
        "Open infrastructure layer that closes the distance between informal "
        "skills and economic opportunity in the age of AI.\n\n"
        "**3 modules, 1 promise:** real data, honest limits, country-agnostic.\n\n"
        "- **Module 01 — Skill Signal Engine** — claude-sonnet-4-5 + ESCO mapping\n"
        "- **Module 02 — Risk Lens** — Frey-Osborne LMIC-adjusted, NetworkX adjacency\n"
        "- **Module 03 — Opportunity & Econometrics** — ILOSTAT signals + matching\n\n"
        "Built for the World Bank Youth Summit × Hack-Nation 5."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — open by design (infrastructure layer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom error handlers
register_exception_handlers(app)

# Routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(config_router, prefix="/api/config", tags=["config"])
app.include_router(profile_router, prefix="/api/profile", tags=["module-01-skills"])
app.include_router(risk_router, prefix="/api/risk", tags=["module-02-risk"])
app.include_router(opportunity_router, prefix="/api/opportunities", tags=["module-03-opportunities"])


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root redirect to /docs."""
    return {
        "service": "UNMAPPED API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/api/health",
    }
