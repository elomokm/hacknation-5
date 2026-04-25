"""Module 01 — Maps raw extracted skills to ESCO taxonomy. Implemented in Phase 1."""

import logging

logger = logging.getLogger(__name__)


def map_to_esco(raw_skills: list[dict]) -> list[dict]:
    """Map a list of raw skill dicts to ESCO skill entries.

    Loads the ESCO subset JSON and performs keyword + embedding match.
    Implemented in Phase 1.
    """
    raise NotImplementedError("Phase 1")
