"""Module 01 — Skill extractor using claude-sonnet-4-5. Implemented in Phase 1."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_skills(text: str, country_code: str = "BEN") -> list[dict]:
    """Extract structured skills from raw free-text description.

    Calls claude-sonnet-4-5 with a structured extraction prompt.
    Returns a list of raw skill dicts before ESCO mapping.
    Implemented in Phase 1.
    """
    raise NotImplementedError("Phase 1")
