"""Module 01 — Generates a StandardizedProfile from mapped skills. Implemented in Phase 1."""

import logging

from core.models import StandardizedProfile

logger = logging.getLogger(__name__)


def build_profile(
    raw_description: str,
    esco_skills: list[dict],
    country_code: str,
) -> StandardizedProfile:
    """Assemble a StandardizedProfile (JSON-LD compatible) from ESCO-mapped skills.

    Implemented in Phase 1.
    """
    raise NotImplementedError("Phase 1")
