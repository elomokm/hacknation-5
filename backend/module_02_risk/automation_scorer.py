"""Module 02 — Automation risk scorer using Frey-Osborne data. Implemented in Phase 2."""

import logging

from core.models import RiskAssessment, StandardizedProfile

logger = logging.getLogger(__name__)


def score_automation_risk(
    profile: StandardizedProfile,
    lmic_adjustment_factor: float = 0.7,
) -> RiskAssessment:
    """Compute LMIC-adjusted automation risk for a StandardizedProfile.

    Loads Frey-Osborne scores, matches by ISCO group, applies config factor.
    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2")
