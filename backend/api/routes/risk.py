"""Module 02 — Risk assessment and projection endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from api.dependencies import (
    get_country_config,
    get_finder,
    get_profile_or_404,
    get_projections,
    get_scorer,
)
from core.models import (
    AdjacentSkill,
    EducationTrajectory,
    RiskAssessment,
)

router = APIRouter()


# ── Request / response models ─────────────────────────────────────────────
class RiskAssessRequest(BaseModel):
    profile_id: str
    country_code: str = "BEN"
    include_adjacent: bool = True


class RiskAssessResponse(BaseModel):
    assessment: RiskAssessment
    adjacent_skills: dict[str, list[AdjacentSkill]]
    note: str


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/assess",
    response_model=RiskAssessResponse,
    summary="Assess automation risk for a stored profile",
    description=(
        "Runs Frey-Osborne LMIC-adjusted scoring per skill. "
        "If include_adjacent=True, also returns adjacent durable alternatives "
        "for every high/critical-risk skill."
    ),
)
async def assess(req: RiskAssessRequest) -> RiskAssessResponse:
    """Assess risk and (optionally) propose adjacent alternatives."""
    config = get_country_config(req.country_code)
    profile = get_profile_or_404(req.profile_id)
    scorer = get_scorer()
    finder = get_finder()

    assessment = scorer.score_profile(profile, config)

    adjacent: dict[str, list[AdjacentSkill]] = {}
    if req.include_adjacent:
        for skill, score in zip(profile.skills, assessment.per_skill_scores):
            if score.risk_band in {"high", "critical"}:
                alternatives = finder.find_durable_alternatives(
                    current_skill=skill,
                    risk_score=score,
                    scorer=scorer,
                    config=config,
                    top_k=3,
                )
                adjacent[skill.esco_id] = alternatives

    return RiskAssessResponse(
        assessment=assessment,
        adjacent_skills=adjacent,
        note=(
            "All risk values are LMIC-adjusted Frey-Osborne probabilities — "
            "directional, not predictive. See assessment.limitations for full caveats."
        ),
    )


@router.get(
    "/projections/{country_code}",
    response_model=EducationTrajectory,
    summary="Wittgenstein education trajectory",
    description=(
        "West Africa SSP2 education attainment projections 2025–2035 "
        "for the country's region. Used to contextualize skill investment decisions."
    ),
)
async def projections(country_code: str) -> EducationTrajectory:
    """Return education trajectory for a country's region."""
    config = get_country_config(country_code)
    loader = get_projections()
    return loader.get_education_trajectory(config)
