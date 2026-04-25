"""Module 03 — Matches a StandardizedProfile to local opportunities. Implemented in Phase 3."""

import logging

from core.models import MatchResult, RiskAssessment, StandardizedProfile

logger = logging.getLogger(__name__)


def match_opportunities(
    profile: StandardizedProfile,
    risk: RiskAssessment,
    country_code: str,
    top_k: int = 5,
) -> list[MatchResult]:
    """Return top-k ranked MatchResults for a given profile and country.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3")
