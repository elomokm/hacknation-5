"""Module 03 — Opportunity registry loader. Implemented in Phase 3."""

import logging
from pathlib import Path

from core.models import Opportunity

logger = logging.getLogger(__name__)


def load_opportunities(country_code: str) -> list[Opportunity]:
    """Load opportunity registry for a given country.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3")
