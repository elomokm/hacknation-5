"""Health and metadata endpoints."""

import os

from fastapi import APIRouter

router = APIRouter()

_VERSION = "1.0.0"


@router.get("/health", summary="Health check")
async def health() -> dict:
    """Liveness probe — returns service status and active country."""
    return {
        "status": "ok",
        "version": _VERSION,
        "active_country": os.getenv("ACTIVE_COUNTRY", "BEN").upper(),
        "service": "UNMAPPED API",
    }


@router.get("/info", summary="Project metadata")
async def info() -> dict:
    """Project metadata: modules, data sources, build info."""
    return {
        "service": "UNMAPPED API",
        "version": _VERSION,
        "challenge": "World Bank Youth Summit × Hack-Nation 5",
        "modules": [
            {
                "id": "module_01_skills",
                "name": "Skill Signal Engine",
                "endpoints": ["POST /api/profile/extract", "POST /api/profile/generate"],
                "uses_llm": True,
                "model": "claude-sonnet-4-5",
            },
            {
                "id": "module_02_risk",
                "name": "AI Readiness & Displacement Risk",
                "endpoints": ["POST /api/risk/assess", "GET /api/risk/projections/{country}"],
                "uses_llm": False,
                "data_source": "Frey-Osborne 2017 + ESCO + Wittgenstein",
            },
            {
                "id": "module_03_opportunity",
                "name": "Opportunity Matching & Econometrics",
                "endpoints": [
                    "POST /api/opportunities/match",
                    "GET /api/opportunities/{country}/signals",
                    "GET /api/opportunities/{country}/dashboard/youth",
                    "GET /api/opportunities/{country}/dashboard/policymaker",
                ],
                "uses_llm": False,
                "data_source": "ILOSTAT 2024 + opportunity registry per country",
            },
        ],
        "data_sources": [
            "ESCO v1.2",
            "ISCO-08 (ILO)",
            "Frey-Osborne 2017",
            "ILOSTAT 2024",
            "Wittgenstein Centre SSP2",
        ],
        "supported_countries": ["BEN", "SEN"],
        "design_principle": "Country-specific parameters are CONFIG, not code.",
    }
