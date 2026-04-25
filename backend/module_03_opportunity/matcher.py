"""Module 03 — Opportunity matcher: profile → ranked OpportunityMatch list.

No LLM calls. Pure scoring algorithm.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.models import (
    CountryConfig,
    Opportunity,
    OpportunityMatch,
    StandardizedProfile,
)

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent


def _build_edu_rank(config: CountryConfig) -> dict[str, int]:
    """Build education rank dict from country config levels list."""
    return {level: i for i, level in enumerate(config.education_taxonomy.levels)}


class OpportunityMatcher:
    """Matches a StandardizedProfile against country-specific opportunities."""

    def __init__(self, config: CountryConfig) -> None:
        """Load and filter opportunities from the country config."""
        self._config = config
        self._edu_rank = _build_edu_rank(config)
        self._opportunities: list[Opportunity] = self._load_opportunities()
        logger.info(
            "OpportunityMatcher ready: %d opportunities loaded for %s",
            len(self._opportunities),
            config.country_code,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(
        self, profile: StandardizedProfile, top_k: int = 5
    ) -> list[OpportunityMatch]:
        """Return top-k OpportunityMatch for the given profile."""
        profile_isco = {
            code for skill in profile.skills for code in skill.isco_groups
        }
        profile_esco = {skill.esco_id for skill in profile.skills}
        profile_edu_rank = self._edu_rank.get(
            profile.education.get("level", "aucun"), 0
        )

        results: list[OpportunityMatch] = []
        for opp in self._opportunities:
            if not opp.realistic_for_youth:
                continue  # no aspirational matching

            match = self._score(opp, profile_isco, profile_esco, profile_edu_rank)
            if match is not None:
                results.append(match)

        results.sort(key=lambda m: m.fit_score, reverse=True)
        logger.info(
            "Matched %d opportunities for profile %s",
            len(results),
            profile.profile_id,
        )
        return results[:top_k]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_opportunities(self) -> list[Opportunity]:
        """Load and type-filter opportunities from JSON."""
        path = _BACKEND_DIR / self._config.opportunities.source_file
        raw = json.loads(path.read_text(encoding="utf-8"))
        enabled = set(self._config.opportunities.types_enabled)
        opps = [Opportunity(**o) for o in raw if o["type"] in enabled]
        return opps

    def _score(
        self,
        opp: Opportunity,
        profile_isco: set[str],
        profile_esco: set[str],
        profile_edu_rank: int,
    ) -> Optional[OpportunityMatch]:
        """Compute fit_score for one opportunity. Returns None if clearly unfit."""
        # 1. ISCO overlap
        opp_isco = set(opp.required_skills_isco)
        matched_isco = sorted(profile_isco & opp_isco)
        isco_ratio = len(matched_isco) / len(opp_isco) if opp_isco else 0.0

        # 2. Education match
        opp_edu_rank = self._edu_rank.get(opp.education_min, 0)
        if profile_edu_rank == opp_edu_rank:
            edu_score = 1.0
        elif profile_edu_rank > opp_edu_rank:
            edu_score = 0.5  # overqualified — still acceptable
        else:
            edu_score = 0.0  # does not meet minimum education

        # 3. Sector signal (ISCO overlap also covers sector match)
        sector_score = 1.0 if matched_isco else 0.0

        # 4. Youth realism (always 1.0 here since we pre-filtered)
        youth_score = 1.0

        fit = (
            0.50 * isco_ratio
            + 0.20 * edu_score
            + 0.20 * sector_score
            + 0.10 * youth_score
        )

        # Gap analysis
        gap_skills = [
            eid for eid in opp.required_skills_esco if eid not in profile_esco
        ]
        gap_education = (
            f"Requires {opp.education_min} (you have {self._config.education_taxonomy.levels[profile_edu_rank]})"
            if edu_score == 0.0
            else None
        )

        # Wage delta
        opp_median_xof = (opp.wage_range_xof[0] + opp.wage_range_xof[1]) // 2
        usd_rate = self._config.labor_data.usd_conversion_rate
        wage_delta = {
            "opportunity_median_xof": opp_median_xof,
            "opportunity_median_usd": round(opp_median_xof / usd_rate),
        }

        # Accessibility note
        if fit >= 0.6:
            note = "Strong match — most requirements align with your current profile."
        elif fit >= 0.35:
            note = "Partial match — some skills gap, but reachable with targeted learning."
        else:
            note = "Stretch match — significant skill or education gap to bridge."

        return OpportunityMatch(
            opportunity=opp,
            fit_score=round(fit, 4),
            matched_isco=matched_isco,
            gap_skills=gap_skills,
            gap_education=gap_education,
            wage_delta=wage_delta,
            accessibility_note=note,
        )
