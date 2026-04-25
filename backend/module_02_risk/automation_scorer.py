"""Module 02 — Automation scorer: Frey-Osborne risk per skill, LMIC-adjusted.

No LLM calls. Pure data lookup + arithmetic.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.models import (
    AutomationScore,
    CountryConfig,
    MappedSkill,
    RiskAssessment,
    SkillRiskScore,
    StandardizedProfile,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

_RISK_BANDS = [
    (0.30, "low"),
    (0.60, "moderate"),
    (0.85, "high"),
    (1.01, "critical"),
]

_LIMITATIONS = [
    "Frey-Osborne (2017) was calibrated on US O*NET task data — task compositions differ in LMIC economies.",
    "LMIC adjustment factor is a pragmatic correction, not an empirically validated calibration for this country.",
    "Matching is at ISCO 2-digit group level; actual automation risk varies widely within each group.",
    "Probabilities reflect computerisation potential, not actual displacement timeline or pace.",
    "New technology adoption lags in LMIC economies may reduce near-term risk relative to these estimates.",
]


def _classify_band(probability: float) -> str:
    """Return the risk band label for a given adjusted probability."""
    for threshold, label in _RISK_BANDS:
        if probability < threshold:
            return label
    return "critical"


class AutomationScorer:
    """Scores automation risk for mapped skills using Frey-Osborne data."""

    def __init__(self) -> None:
        """Load Frey-Osborne scores once at init time."""
        path = _DATA_DIR / "frey_osborne" / "automation_scores.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._scores: list[AutomationScore] = [AutomationScore(**s) for s in raw]
        # Build lookup: isco_code → list[AutomationScore]
        self._by_isco: dict[str, list[AutomationScore]] = {}
        for score in self._scores:
            self._by_isco.setdefault(score.isco_match, []).append(score)
        logger.info(
            "AutomationScorer ready: %d occupations across %d ISCO groups",
            len(self._scores),
            len(self._by_isco),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_profile(
        self, profile: StandardizedProfile, config: CountryConfig
    ) -> RiskAssessment:
        """Score all skills in a profile and return a RiskAssessment."""
        lmic_factor = config.automation_calibration.lmic_adjustment_factor

        per_skill: list[SkillRiskScore] = [
            self.score_skill(
                esco_id=skill.esco_id,
                esco_label=skill.esco_label,
                isco_groups=skill.isco_groups,
                lmic_factor=lmic_factor,
            )
            for skill in profile.skills
        ]

        matched = [s for s in per_skill if s.adjusted_probability is not None]
        weighted_avg = (
            sum(s.adjusted_probability for s in matched) / len(matched)
            if matched else 0.0
        )
        at_risk_count = sum(
            1 for s in per_skill if s.risk_band in {"high", "critical"}
        )
        pct_at_risk = at_risk_count / len(per_skill) if per_skill else 0.0

        overall_band = _classify_band(weighted_avg) if matched else "no_match"

        methodology_note = (
            f"Risk scores derived from Frey-Osborne (2017) US occupation probabilities, "
            f"adjusted by LMIC factor {lmic_factor:.2f} for {config.country}. "
            f"Matching is at ISCO 2-digit group level (confidence: 'isco_proxy'). "
            f"Treat values as directional, not predictive."
        )

        return RiskAssessment(
            profile_id=profile.profile_id,
            country_code=config.country_code,
            per_skill_scores=per_skill,
            overall_risk_band=overall_band,
            weighted_average_probability=round(weighted_avg, 4),
            pct_skills_at_risk=round(pct_at_risk, 4),
            methodology_note=methodology_note,
            limitations=_LIMITATIONS,
        )

    def score_skill(
        self,
        esco_id: str,
        esco_label: str,
        isco_groups: list[str],
        lmic_factor: float,
    ) -> SkillRiskScore:
        """Score one skill by its ISCO groups using Frey-Osborne lookup."""
        matched: list[AutomationScore] = []
        for code in isco_groups:
            matched.extend(self._by_isco.get(code, []))

        if not matched:
            return SkillRiskScore(
                esco_id=esco_id,
                esco_label=esco_label,
                raw_frey_osborne=None,
                lmic_adjustment_applied=lmic_factor,
                adjusted_probability=None,
                risk_band="no_match",
                matched_occupations=[],
                confidence="no_match",
            )

        raw_mean = sum(s.automation_probability for s in matched) / len(matched)
        adjusted = min(1.0, raw_mean * lmic_factor)

        return SkillRiskScore(
            esco_id=esco_id,
            esco_label=esco_label,
            raw_frey_osborne=round(raw_mean, 4),
            lmic_adjustment_applied=lmic_factor,
            adjusted_probability=round(adjusted, 4),
            risk_band=_classify_band(adjusted),
            matched_occupations=[s.occupation for s in matched],
            confidence="isco_proxy",
        )
