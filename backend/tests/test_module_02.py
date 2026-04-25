"""Module 02 test — automation risk, adjacent skills, education projections.

No LLM calls. Uses a hardcoded StandardizedProfile based on Akossiwa (Phase 3 output).
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from core.config_loader import load_config
from core.models import ExtractedSkill, MappedSkill, StandardizedProfile
from module_02_risk.automation_scorer import AutomationScorer
from module_02_risk.adjacent_skills import AdjacentSkillsFinder
from module_02_risk.projection_loader import ProjectionLoader

_DIV = "=" * 65

# ------------------------------------------------------------------
# Hardcoded Akossiwa profile (Phase 3 canonical output — no LLM needed)
# ------------------------------------------------------------------

def _make_extracted(raw: str, norm: str, cat: str, conf: float, ev: str) -> ExtractedSkill:
    return ExtractedSkill(raw_label=raw, normalized_label=norm, category=cat, confidence=conf, evidence=ev)


AKOSSIWA_PROFILE = StandardizedProfile(
    profile_id="test_akossiwa_mod02",
    generated_at=datetime.now(timezone.utc),
    country_code="BEN",
    name="Akossiwa",
    education={"level": "BEPC", "isced": 2, "isced_label": "Lower secondary education", "country_taxonomy": "BEN"},
    languages=["fr", "fon"],
    skills=[
        MappedSkill(
            esco_id="esco:skill:0003",
            esco_label="repair mobile phone charging ports and batteries",
            esco_category="Mobile Repair",
            isco_groups=["74"],
            isco_titles=["Electrical and Electronic Trades Workers"],
            match_confidence=0.7,
            raw_extraction=_make_extracted(
                "répare des téléphones", "Mobile Phone Repair",
                "Mobile Repair", 1.0, "Je répare des téléphones depuis 4 ans",
            ),
        ),
        MappedSkill(
            esco_id="esco:skill:0005",
            esco_label="write HTML markup for web pages",
            esco_category="Web Development",
            isco_groups=["25"],
            isco_titles=["Information and Communications Technology Professionals"],
            match_confidence=0.37,
            raw_extraction=_make_extracted(
                "appris HTML", "HTML Programming",
                "Web Development", 0.6, "J'ai appris HTML sur YouTube",
            ),
        ),
        MappedSkill(
            esco_id="esco:skill:0072",
            esco_label="manage product inventory and stock levels",
            esco_category="Commerce",
            isco_groups=["43", "52", "24"],
            isco_titles=["Numerical and Material Recording Clerks", "Sales Workers", "Business Professionals"],
            match_confidence=0.6,
            raw_extraction=_make_extracted(
                "tiens son inventaire sur Excel", "Inventory Management",
                "Commerce", 0.6, "je tiens son inventaire sur Excel",
            ),
        ),
        MappedSkill(
            esco_id="esco:skill:0054",
            esco_label="handle customer complaints and service recovery",
            esco_category="General Service",
            isco_groups=["51", "52", "42", "54"],
            isco_titles=["Personal Service Workers", "Sales Workers", "Customer Services Clerks", "Protective Services Workers"],
            match_confidence=0.4,
            raw_extraction=_make_extracted(
                "aide ma cousine à gérer son magasin", "Customer Service",
                "Commerce", 0.4, "J'aide ma cousine à gérer son magasin de tissus",
            ),
        ),
    ],
    skill_categories={"Mobile Repair": 1, "Web Development": 1, "Commerce": 1, "General Service": 1},
    portability={
        "isco_codes": ["24", "25", "42", "43", "51", "52", "54", "74"],
        "esco_count": 4, "unmapped_skill_count": 2,
        "format_version": "1.0", "standard": "ESCO v1.2 / ISCO-08",
    },
    human_readable_summary="Akossiwa has mobile repair, web, and commerce skills.",
)


if __name__ == "__main__":
    config = load_config("BEN")
    scorer = AutomationScorer()
    finder = AdjacentSkillsFinder()
    loader = ProjectionLoader()

    # ──────────────────────────────────────────────────────────────
    # 1. AutomationScorer
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 02 — Automation Risk Assessment")
    logger.info(_DIV)

    assessment = scorer.score_profile(AKOSSIWA_PROFILE, config)

    logger.info("Profile : %s  |  Country: %s", assessment.profile_id, assessment.country_code)
    logger.info("Overall risk band          : %s", assessment.overall_risk_band)
    logger.info("Weighted avg probability   : %.3f", assessment.weighted_average_probability)
    logger.info("%% skills at high/critical  : %.0f%%", assessment.pct_skills_at_risk * 100)
    logger.info("")
    logger.info("Per-skill risk table:")
    logger.info("  %-42s  %-8s  %-6s  %-6s  %s",
                "ESCO label", "band", "raw", "adj", "matched occupations")
    logger.info("  " + "-" * 100)
    for s in assessment.per_skill_scores:
        raw = f"{s.raw_frey_osborne:.3f}" if s.raw_frey_osborne is not None else "  n/a"
        adj = f"{s.adjusted_probability:.3f}" if s.adjusted_probability is not None else "  n/a"
        occ = ", ".join(s.matched_occupations[:2]) + ("…" if len(s.matched_occupations) > 2 else "")
        logger.info("  %-42s  %-8s  %s  %s  %s",
                    s.esco_label[:42], s.risk_band, raw, adj, occ[:60])

    logger.info("")
    logger.info("Methodology: %s", assessment.methodology_note)
    logger.info("Limitations (%d):", len(assessment.limitations))
    for lim in assessment.limitations:
        logger.info("  • %s", lim)

    # ──────────────────────────────────────────────────────────────
    # 2. AdjacentSkillsFinder — for each high-risk skill
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 02 — Adjacent Durable Skills")
    logger.info(_DIV)

    high_risk_found = False
    for skill, risk_score in zip(AKOSSIWA_PROFILE.skills, assessment.per_skill_scores):
        if risk_score.risk_band not in {"high", "critical"}:
            continue
        high_risk_found = True
        logger.info("High-risk skill: %s (band=%s, adj=%.3f)",
                    skill.esco_label, risk_score.risk_band,
                    risk_score.adjusted_probability or 0)
        alts = finder.find_durable_alternatives(skill, risk_score, scorer, config, top_k=3)
        if alts:
            for alt in alts:
                adj = alt.automation_risk.adjusted_probability
                logger.info(
                    "  → %-42s [%s] adj=%.3f  prox=%.2f",
                    alt.esco_label[:42], alt.automation_risk.risk_band,
                    adj if adj is not None else 0.0, alt.proximity_score,
                )
                logger.info("     %s", alt.transition_rationale)
        else:
            logger.info("  No durable alternatives found in graph.")

    # ──────────────────────────────────────────────────────────────
    # 3. ProjectionLoader
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 02 — Education Trajectory (West Africa 2025→2035)")
    logger.info(_DIV)

    trajectory = loader.get_education_trajectory(config)
    logger.info("Region: %s  |  Scenario: %s", trajectory.region, trajectory.scenario)
    logger.info("Education distribution 2025 → 2035:")
    for level in trajectory.summary_2025:
        s25 = trajectory.summary_2025[level]
        s35 = trajectory.summary_2035.get(level, 0.0)
        logger.info("  %-28s  %5.1f%% → %5.1f%%  (%+.1f pp)", level, s25, s35, s35 - s25)
    logger.info("")
    logger.info("Key shifts:")
    for shift in trajectory.key_shifts:
        logger.info("  • %s", shift)

    logger.info("")
    logger.info("Skill-level contextualisation:")
    for skill in AKOSSIWA_PROFILE.skills[:2]:
        ctx = loader.contextualize_for_skill(skill, trajectory)
        logger.info("  [%s] %s", skill.esco_label[:30], ctx)

    # ──────────────────────────────────────────────────────────────
    # Assertions
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Running assertions...")

    # All skills have valid risk_band
    valid_bands = {"low", "moderate", "high", "critical", "no_match"}
    for s in assessment.per_skill_scores:
        assert s.risk_band in valid_bands, f"Invalid band: {s.risk_band}"

    # LMIC factor was actually applied (raw ≠ adjusted where matched)
    lmic_applied = False
    for s in assessment.per_skill_scores:
        if s.raw_frey_osborne is not None and s.adjusted_probability is not None:
            assert abs(s.adjusted_probability - s.raw_frey_osborne * config.automation_calibration.lmic_adjustment_factor) < 0.001
            lmic_applied = True
    assert lmic_applied, "LMIC factor never applied — no matched skills?"

    # At least 1 high-risk skill in Akossiwa's profile
    high_or_critical = [s for s in assessment.per_skill_scores if s.risk_band in {"high", "critical"}]
    assert len(high_or_critical) >= 1, "Expected ≥1 high-risk skill for Akossiwa"

    # Each high-risk skill produces ≥1 durable alternative
    for skill, risk_score in zip(AKOSSIWA_PROFILE.skills, assessment.per_skill_scores):
        if risk_score.risk_band in {"high", "critical"}:
            alts = finder.find_durable_alternatives(skill, risk_score, scorer, config, top_k=3)
            assert len(alts) >= 1, f"No alternatives for high-risk skill {skill.esco_label}"

    # Limitations list non-empty
    assert len(assessment.limitations) >= 3, "limitations list too short"

    # Trajectory has 2025 and 2035 data
    assert "Upper secondary" in trajectory.summary_2025
    assert "Upper secondary" in trajectory.summary_2035
    assert len(trajectory.key_shifts) >= 1

    logger.info("")
    logger.info(_DIV)
    logger.info("ALL MODULE 02 ASSERTIONS PASSED")
    logger.info(_DIV)
