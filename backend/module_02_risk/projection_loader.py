"""Module 02 — Loads Wittgenstein Centre education projections. Implemented in Phase 2."""

import logging
from pathlib import Path

from core.models import ProjectionPoint

logger = logging.getLogger(__name__)


def load_projections(source_file: str, region: str = "West Africa") -> list[ProjectionPoint]:
    """Load and filter Wittgenstein projections for a given region.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2")
