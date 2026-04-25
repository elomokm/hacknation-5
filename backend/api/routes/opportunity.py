"""Module 03 — Opportunity matching, econometric signals, dashboards."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.dependencies import (
    get_country_config,
    get_econ,
    get_finder,
    get_matcher,
    get_profile_or_404,
    get_scorer,
)
from core.models import (
    OpportunityMatch,
    PolicymakerDashboard,
    SectorGrowthSignal,
    WageSignal,
    YouthDashboard,
)
from module_03_opportunity.dashboards import (
    generate_policymaker_dashboard,
    generate_youth_dashboard,
)

router = APIRouter()


# ── Request / response models ─────────────────────────────────────────────
class MatchRequest(BaseModel):
    profile_id: str
    country_code: str = "BEN"
    top_k: int = 5
    type_filter: Optional[list[str]] = None


class MatchResponse(BaseModel):
    matches: list[OpportunityMatch]
    wage_signal: WageSignal
    growth_signal: SectorGrowthSignal


class SignalsResponse(BaseModel):
    wage: WageSignal
    growth: SectorGrowthSignal
    note: str


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Match a profile to local opportunities",
    description=(
        "Returns top-k OpportunityMatch results for a stored profile, "
        "filtered to realistic_for_youth=True. Includes wage and growth signals."
    ),
)
async def match(req: MatchRequest) -> MatchResponse:
    """Match profile to opportunities and surface econometric signals."""
    profile = get_profile_or_404(req.profile_id)
    matcher = get_matcher(req.country_code)
    econ = get_econ(req.country_code)

    matches = matcher.match(profile, top_k=req.top_k)
    if req.type_filter:
        type_set = set(req.type_filter)
        matches = [m for m in matches if m.opportunity.type in type_set]

    return MatchResponse(
        matches=matches,
        wage_signal=econ.get_wage_signals(profile),
        growth_signal=econ.get_growth_signals(),
    )


@router.get(
    "/{country_code}/signals",
    response_model=SignalsResponse,
    summary="Get the 2 econometric signals for a country",
    description=(
        "Returns wage signal (current vs formal) and sector growth signal. "
        "These are the 2 required econometric signals from the brief — "
        "policymakers can query directly without going through a profile."
    ),
)
async def signals(
    country_code: str,
    profile_id: Optional[str] = Query(None, description="Optional profile_id for personalised wage estimate"),
) -> SignalsResponse:
    """Surface the 2 econometric signals for a country (optionally personalised)."""
    config = get_country_config(country_code)
    econ = get_econ(country_code)

    if profile_id:
        profile = get_profile_or_404(profile_id)
        wage = econ.get_wage_signals(profile)
    else:
        # Synthesise a placeholder profile for population-level wage estimate
        from datetime import datetime, timezone
        from core.models import StandardizedProfile
        placeholder = StandardizedProfile(
            profile_id="population",
            generated_at=datetime.now(timezone.utc),
            country_code=config.country_code,
            name="Population",
            education={"level": config.education_taxonomy.levels[0], "isced": 0},
            languages=[config.ui.primary_language],
            skills=[],
            skill_categories={},
            portability={"isco_codes": [], "esco_count": 0, "format_version": "1.0"},
            human_readable_summary="",
        )
        wage = econ.get_wage_signals(placeholder)

    return SignalsResponse(
        wage=wage,
        growth=econ.get_growth_signals(),
        note=(
            "Wage data: ILOSTAT 2024 sector medians. Growth signal is based on "
            "wage premium and strategic priority — not a time-series growth rate."
        ),
    )


@router.get(
    "/{country_code}/dashboard/youth",
    response_model=YouthDashboard,
    summary="Youth-facing dashboard for a stored profile",
    description=(
        "Composite endpoint: runs risk + match + signals + dashboard assembly "
        "for a stored profile. Returns the full youth dashboard."
    ),
)
async def youth_dashboard(
    country_code: str,
    profile_id: str = Query(..., description="ID of a previously generated profile"),
) -> YouthDashboard:
    """Assemble the full youth dashboard for a stored profile."""
    config = get_country_config(country_code)
    profile = get_profile_or_404(profile_id)

    scorer = get_scorer()
    matcher = get_matcher(country_code)
    econ = get_econ(country_code)

    risk = scorer.score_profile(profile, config)
    matches = matcher.match(profile, top_k=5)
    wage_signal = econ.get_wage_signals(profile)
    growth_signal = econ.get_growth_signals()

    return generate_youth_dashboard(
        profile, risk, matches, wage_signal, growth_signal, config
    )


@router.get(
    "/{country_code}/dashboard/policymaker",
    response_model=PolicymakerDashboard,
    summary="Policymaker aggregate dashboard",
    description=(
        "Returns ILOSTAT-driven aggregate signals for a country: youth unemployment, "
        "informal share, sector employment, recommended program areas."
    ),
)
async def policymaker_dashboard(country_code: str) -> PolicymakerDashboard:
    """Return the country-level policymaker aggregate dashboard."""
    config = get_country_config(country_code)
    return generate_policymaker_dashboard(config, all_profiles=None)
