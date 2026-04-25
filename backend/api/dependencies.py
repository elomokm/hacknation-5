"""Shared FastAPI dependencies and module singletons."""

import logging
from typing import Optional

from fastapi import HTTPException

from core.config_loader import load_config
from core.models import CountryConfig, StandardizedProfile
from module_01_skills.taxonomy_mapper import TaxonomyMapper
from module_02_risk.adjacent_skills import AdjacentSkillsFinder
from module_02_risk.automation_scorer import AutomationScorer
from module_02_risk.projection_loader import ProjectionLoader
from module_03_opportunity.econometrics import EconometricSignals
from module_03_opportunity.matcher import OpportunityMatcher

logger = logging.getLogger(__name__)


# ── Country-agnostic singletons ─────────────────────────────────────────────
_MAPPER: Optional[TaxonomyMapper] = None
_SCORER: Optional[AutomationScorer] = None
_FINDER: Optional[AdjacentSkillsFinder] = None
_PROJECTIONS: Optional[ProjectionLoader] = None

# ── Per-country instances ───────────────────────────────────────────────────
_MATCHERS: dict[str, OpportunityMatcher] = {}
_ECONS: dict[str, EconometricSignals] = {}

# ── In-memory profile store (MVP — not persistent) ──────────────────────────
PROFILE_STORE: dict[str, StandardizedProfile] = {}


def get_country_config(country_code: str = "BEN") -> CountryConfig:
    """FastAPI dependency: load and validate a country config.

    Lets ValueError / FileNotFoundError propagate so the global handlers
    return our structured error format.
    """
    return load_config(country_code)


def get_mapper() -> TaxonomyMapper:
    """Singleton TaxonomyMapper (country-agnostic, lazy-loaded)."""
    global _MAPPER
    if _MAPPER is None:
        _MAPPER = TaxonomyMapper()
    return _MAPPER


def get_scorer() -> AutomationScorer:
    """Singleton AutomationScorer."""
    global _SCORER
    if _SCORER is None:
        _SCORER = AutomationScorer()
    return _SCORER


def get_finder() -> AdjacentSkillsFinder:
    """Singleton AdjacentSkillsFinder."""
    global _FINDER
    if _FINDER is None:
        _FINDER = AdjacentSkillsFinder()
    return _FINDER


def get_projections() -> ProjectionLoader:
    """Singleton ProjectionLoader."""
    global _PROJECTIONS
    if _PROJECTIONS is None:
        _PROJECTIONS = ProjectionLoader()
    return _PROJECTIONS


def get_matcher(country_code: str) -> OpportunityMatcher:
    """Get or create OpportunityMatcher for a country."""
    code = country_code.upper()
    if code not in _MATCHERS:
        _MATCHERS[code] = OpportunityMatcher(load_config(code))
    return _MATCHERS[code]


def get_econ(country_code: str) -> EconometricSignals:
    """Get or create EconometricSignals for a country."""
    code = country_code.upper()
    if code not in _ECONS:
        _ECONS[code] = EconometricSignals(load_config(code))
    return _ECONS[code]


def get_profile_or_404(profile_id: str) -> StandardizedProfile:
    """Look up a stored profile by ID, raise 404 if missing."""
    profile = PROFILE_STORE.get(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Profile {profile_id!r} not found. "
            "Note: in-memory store — profiles are lost on server restart.",
        )
    return profile
