"""Module 03 — Opportunity matching, econometric signals, dashboards.

Includes the ingestion endpoints that let an operator (Ministry, NGO,
training provider, employer) push their own opportunities into UNMAPPED.
This is what makes UNMAPPED end-to-end deployable infrastructure rather
than a closed product — see INTEGRATION.md for the operator guide.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
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
    Opportunity,
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

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent.parent

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


# ── Ingestion endpoints — operators push their own opportunities here ─────
# These endpoints make UNMAPPED end-to-end deployable infrastructure.
# See INTEGRATION.md for the operator guide.

class BulkUpsertRequest(BaseModel):
    """Wrapper for bulk opportunity upserts."""

    opportunities: list[Opportunity]


class IngestionResponse(BaseModel):
    """Response envelope for any ingestion operation."""

    country_code: str
    inserted: int
    updated: int
    deleted: int
    total_in_country: int
    note: str


def _opportunities_path(country_code: str) -> Path:
    """Resolve the opportunities JSON path for a country (validated config)."""
    config = get_country_config(country_code)
    return _BACKEND_DIR / config.opportunities.source_file


def _read_opportunities(path: Path) -> list[dict]:
    """Read raw opportunities list from disk (returns [] if file empty)."""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_opportunities(path: Path, opps: list[dict]) -> None:
    """Atomically rewrite the opportunities JSON file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(opps, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _invalidate_country_caches(country_code: str) -> None:
    """Clear per-country singletons so writes are reflected on next read."""
    from api.dependencies import _ECONS, _MATCHERS
    code = country_code.upper()
    _MATCHERS.pop(code, None)
    _ECONS.pop(code, None)


@router.post(
    "/{country_code}/upsert",
    response_model=IngestionResponse,
    summary="Upsert a single opportunity",
    description=(
        "Add a new opportunity or replace an existing one (matched by `id`). "
        "Validates against the Opportunity schema. Triggers cache invalidation "
        "so the new data is reflected immediately in /match and /signals."
    ),
)
async def upsert_opportunity(
    country_code: str, opp: Opportunity
) -> IngestionResponse:
    """Upsert one opportunity by id."""
    path = _opportunities_path(country_code)
    raw = _read_opportunities(path)

    existing_idx = next(
        (i for i, o in enumerate(raw) if o.get("id") == opp.id), None
    )
    inserted = updated = 0
    if existing_idx is not None:
        raw[existing_idx] = opp.model_dump()
        updated = 1
    else:
        raw.append(opp.model_dump())
        inserted = 1

    _write_opportunities(path, raw)
    _invalidate_country_caches(country_code)
    logger.info(
        "Upsert %s in %s: inserted=%d updated=%d total=%d",
        opp.id, country_code, inserted, updated, len(raw),
    )
    return IngestionResponse(
        country_code=country_code.upper(),
        inserted=inserted,
        updated=updated,
        deleted=0,
        total_in_country=len(raw),
        note="Per-country caches invalidated. Next /match call will use fresh data.",
    )


@router.post(
    "/{country_code}/bulk",
    response_model=IngestionResponse,
    summary="Bulk upsert opportunities",
    description=(
        "Insert or update many opportunities atomically. Matched by `id`. "
        "Use this for periodic ETL jobs (e.g. a weekly batch from BRAC field "
        "officers, or a daily pull from ANPE Bénin's database). All-or-nothing: "
        "either every opportunity validates or none are written."
    ),
)
async def bulk_upsert_opportunities(
    country_code: str, body: BulkUpsertRequest
) -> IngestionResponse:
    """Atomically upsert a batch of opportunities."""
    path = _opportunities_path(country_code)
    raw = _read_opportunities(path)

    existing_ids = {o.get("id"): i for i, o in enumerate(raw)}
    inserted = updated = 0
    for opp in body.opportunities:
        idx = existing_ids.get(opp.id)
        if idx is not None:
            raw[idx] = opp.model_dump()
            updated += 1
        else:
            raw.append(opp.model_dump())
            existing_ids[opp.id] = len(raw) - 1
            inserted += 1

    _write_opportunities(path, raw)
    _invalidate_country_caches(country_code)
    logger.info(
        "Bulk upsert in %s: inserted=%d updated=%d total=%d",
        country_code, inserted, updated, len(raw),
    )
    return IngestionResponse(
        country_code=country_code.upper(),
        inserted=inserted,
        updated=updated,
        deleted=0,
        total_in_country=len(raw),
        note=(
            f"Atomically processed {len(body.opportunities)} opportunities. "
            "Per-country caches invalidated."
        ),
    )


@router.delete(
    "/{country_code}/{opp_id}",
    response_model=IngestionResponse,
    summary="Delete an opportunity by id",
    description="Remove an opportunity from the country registry. 404 if not found.",
)
async def delete_opportunity(
    country_code: str, opp_id: str
) -> IngestionResponse:
    """Delete one opportunity by id; raise 404 if it doesn't exist."""
    path = _opportunities_path(country_code)
    raw = _read_opportunities(path)

    new_raw = [o for o in raw if o.get("id") != opp_id]
    deleted = len(raw) - len(new_raw)
    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Opportunity {opp_id!r} not found in {country_code.upper()}",
        )

    _write_opportunities(path, new_raw)
    _invalidate_country_caches(country_code)
    logger.info("Deleted %s from %s (now %d total)", opp_id, country_code, len(new_raw))
    return IngestionResponse(
        country_code=country_code.upper(),
        inserted=0,
        updated=0,
        deleted=deleted,
        total_in_country=len(new_raw),
        note="Per-country caches invalidated.",
    )


@router.get(
    "/{country_code}",
    response_model=list[Opportunity],
    summary="List all opportunities for a country",
    description="Returns the full opportunity registry for a country.",
)
async def list_opportunities(country_code: str) -> list[Opportunity]:
    """Return all opportunities for a country."""
    path = _opportunities_path(country_code)
    raw = _read_opportunities(path)
    return [Opportunity(**o) for o in raw]
