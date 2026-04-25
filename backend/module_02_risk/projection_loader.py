"""Module 02 — Wittgenstein education projection loader.

No LLM calls. Pure data aggregation.
"""

import json
import logging
from pathlib import Path

from core.models import CountryConfig, EducationTrajectory, MappedSkill, ProjectionPoint

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_SHIFT_THRESHOLD_PCT = 1.5  # minimum % point change to be listed as a key shift

# ISCO groups associated with ICT / professional roles
_ICT_ISCO = {"21", "25", "35"}
# ISCO groups associated with agricultural roles
_AGRI_ISCO = {"61", "62", "92"}


class ProjectionLoader:
    """Loads and surfaces Wittgenstein Centre education projections."""

    def __init__(self) -> None:
        """Load projection data once at init."""
        path = _DATA_DIR / "wittgenstein" / "projections_west_africa.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._meta = raw
        self._points: list[ProjectionPoint] = [
            ProjectionPoint(**p) for p in raw["projections"]
        ]
        logger.info(
            "ProjectionLoader ready: %d data points, region=%s",
            len(self._points),
            raw.get("region"),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_education_trajectory(
        self, config: CountryConfig
    ) -> EducationTrajectory:
        """Assemble an EducationTrajectory with key shifts 2025→2035."""
        summary_2025 = {
            p.education_level: p.share_youth_pct
            for p in self._points if p.year == 2025
        }
        summary_2035 = {
            p.education_level: p.share_youth_pct
            for p in self._points if p.year == 2035
        }

        key_shifts: list[str] = []
        for level, share_25 in summary_2025.items():
            share_35 = summary_2035.get(level)
            if share_35 is None:
                continue
            delta = share_35 - share_25
            if abs(delta) >= _SHIFT_THRESHOLD_PCT:
                direction = "rising" if delta > 0 else "declining"
                key_shifts.append(
                    f"{level} share {direction} from "
                    f"{share_25:.1f}% → {share_35:.1f}% "
                    f"({delta:+.1f} pp)"
                )

        # Sort: largest absolute shifts first
        key_shifts.sort(
            key=lambda s: abs(float(s.split("(")[1].split(" ")[0])),
            reverse=True,
        )

        logger.info(
            "Education trajectory built: %d key shifts identified", len(key_shifts)
        )
        return EducationTrajectory(
            region=self._meta.get("region", "West Africa"),
            scenario=self._meta.get("scenario", "SSP2"),
            timeline=self._points,
            summary_2025=summary_2025,
            summary_2035=summary_2035,
            key_shifts=key_shifts,
        )

    def contextualize_for_skill(
        self, skill: MappedSkill, trajectory: EducationTrajectory
    ) -> str:
        """Return a 1-sentence education context for a given mapped skill."""
        post_25 = trajectory.summary_2025.get("Post-secondary", 0.0)
        post_35 = trajectory.summary_2035.get("Post-secondary", 0.0)
        upper_25 = trajectory.summary_2025.get("Upper secondary", 0.0)
        upper_35 = trajectory.summary_2035.get("Upper secondary", 0.0)
        no_ed_25 = trajectory.summary_2025.get("No education", 0.0)
        no_ed_35 = trajectory.summary_2035.get("No education", 0.0)

        isco_set = set(skill.isco_groups)

        if isco_set & _ICT_ISCO:
            return (
                f"By 2035, post-secondary attainment in West Africa rises to "
                f"{post_35:.1f}% (from {post_25:.1f}% in 2025) — "
                f"competitive entry to {skill.esco_category} roles requires "
                f"staying ahead of this credential curve."
            )
        elif isco_set & _AGRI_ISCO:
            return (
                f"No-education share is declining from {no_ed_25:.1f}% to "
                f"{no_ed_35:.1f}% — agricultural workers without formal credentials "
                f"face increasing competition from more-educated labour market entrants."
            )
        else:
            return (
                f"Upper secondary attainment is projected to reach {upper_35:.1f}% "
                f"by 2035 (vs {upper_25:.1f}% today) — building certified skills "
                f"now provides a durable competitive advantage in {skill.esco_category}."
            )
