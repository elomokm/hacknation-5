"""Module 03 — Econometric signal computation from ILOSTAT data. Implemented in Phase 3."""

import logging

from core.models import LaborMarketData, Opportunity

logger = logging.getLogger(__name__)


def compute_income_delta(
    current_median_usd: int,
    opportunity: Opportunity,
    labor_data: LaborMarketData,
) -> int:
    """Compute USD income delta between current situation and opportunity.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3")


def get_sector_signal(sector: str, labor_data: LaborMarketData) -> dict:
    """Return wage and employment share signals for a sector.

    Returns dict with keys: median_monthly_usd, employment_share_pct.
    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3")
