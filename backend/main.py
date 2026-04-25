"""UNMAPPED — FastAPI orchestrator."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UNMAPPED API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Health check with active country."""
    import os
    return {"status": "ok", "project": "UNMAPPED", "country": os.getenv("ACTIVE_COUNTRY", "BEN")}


@app.post("/analyze")
async def analyze(_body: dict) -> dict:
    """Full pipeline: extract → risk → match. Implemented in Phases 1–3."""
    return {"status": "not_implemented", "phase": "0"}
