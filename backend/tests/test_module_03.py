"""Module 03 test — opportunity matching, econometric signals, dashboards.

No LLM calls. Uses Akossiwa hardcoded profile from Phase 3/4.
"""

import json
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
from core.models import ExtractedSkill, MappedSkill, RiskAssessment, SkillRiskScore, StandardizedProfile
from module_02_risk.automation_scorer import AutomationScorer
from module_03_opportunity.matcher import OpportunityMatcher
from module_03_opportunity.econometrics import EconometricSignals
from module_03_opportunity.dashboards import generate_youth_dashboard, generate_policymaker_dashboard

_DIV = "=" * 65


def _make_extracted(raw, norm, cat, conf, ev):
    return ExtractedSkill(raw_label=raw, normalized_label=norm, category=cat, confidence=conf, evidence=ev)


AKOSSIWA = StandardizedProfile(
    profile_id="test_akossiwa_mod03",
    generated_at=datetime.now(timezone.utc),
    country_code="BEN",
    name="Akossiwa",
    education={"level": "BEPC", "isced": 2, "isced_label": "Lower secondary education", "country_taxonomy": "BEN"},
    languages=["fr", "fon"],
    skills=[
        MappedSkill(esco_id="esco:skill:0003", esco_label="repair mobile phone charging ports and batteries",
                    esco_category="Mobile Repair", isco_groups=["74"], isco_titles=["Electrical and Electronic Trades Workers"],
                    match_confidence=0.7, raw_extraction=_make_extracted("répare des téléphones", "Mobile Phone Repair", "Mobile Repair", 1.0, "4 ans")),
        MappedSkill(esco_id="esco:skill:0005", esco_label="write HTML markup for web pages",
                    esco_category="Web Development", isco_groups=["25"], isco_titles=["ICT Professionals"],
                    match_confidence=0.37, raw_extraction=_make_extracted("HTML", "HTML Programming", "Web Development", 0.6, "YouTube")),
        MappedSkill(esco_id="esco:skill:0072", esco_label="manage product inventory and stock levels",
                    esco_category="Commerce", isco_groups=["43", "52", "24"], isco_titles=["Clerks", "Sales", "Business"],
                    match_confidence=0.6, raw_extraction=_make_extracted("inventaire Excel", "Inventory Management", "Commerce", 0.6, "Excel")),
        MappedSkill(esco_id="esco:skill:0054", esco_label="handle customer complaints and service recovery",
                    esco_category="General Service", isco_groups=["51", "52", "42", "54"], isco_titles=["Service", "Sales", "Clerks", "Security"],
                    match_confidence=0.4, raw_extraction=_make_extracted("service clients", "Customer Service", "Commerce", 0.4, "magasin")),
    ],
    skill_categories={"Mobile Repair": 1, "Web Development": 1, "Commerce": 1, "General Service": 1},
    portability={"isco_codes": ["24", "25", "42", "43", "51", "52", "54", "74"], "esco_count": 4,
                 "unmapped_skill_count": 2, "format_version": "1.0", "standard": "ESCO v1.2 / ISCO-08"},
    human_readable_summary=(
        "Akossiwa répare des téléphones depuis 4 ans à Cotonou et maîtrise HTML "
        "et la gestion de stocks sur Excel. Son profil combine compétences techniques "
        "et commerciales — une combinaison valorisable dans le secteur numérique et "
        "la distribution formelle au Bénin."
    ),
)


if __name__ == "__main__":
    config = load_config("BEN")
    scorer = AutomationScorer()
    matcher = OpportunityMatcher(config)
    econ = EconometricSignals(config)

    # ── Risk assessment (from Phase 4, needed for dashboard)
    risk = scorer.score_profile(AKOSSIWA, config)

    # ──────────────────────────────────────────────────────────────
    # 1. Opportunity Matching
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 03 — Opportunity Matching")
    logger.info(_DIV)

    matches = matcher.match(AKOSSIWA, top_k=5)
    logger.info("Top %d matches for Akossiwa:", len(matches))
    logger.info("  %-40s  %-6s  %-12s  %s", "Title", "Score", "Type", "Wage range XOF")
    logger.info("  " + "-" * 90)
    for m in matches:
        o = m.opportunity
        logger.info("  %-40s  %.3f  %-12s  %s",
                    o.title[:40], m.fit_score, o.type,
                    f"{o.wage_range_xof[0]:,}–{o.wage_range_xof[1]:,}")
        logger.info("    ISCO matched: %s | Gap skills: %d | %s",
                    m.matched_isco, len(m.gap_skills), m.accessibility_note)

    # ──────────────────────────────────────────────────────────────
    # 2. Econometric Signals
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 03 — Econometric Signal 1: Wage Mirror")
    logger.info(_DIV)

    wage_signal = econ.get_wage_signals(AKOSSIWA)
    logger.info("Current estimated income : %s XOF/month (%d USD)",
                f"{wage_signal.current_estimated_xof:,}", wage_signal.current_estimated_usd)
    logger.info("Wage gap to best match   : %s XOF (×%.1f)",
                f"{wage_signal.wage_gap_to_best_match_xof:,}", wage_signal.wage_gap_multiplier)
    logger.info("Formal wages by sector:")
    for sector, xof in sorted(wage_signal.formal_median_xof_by_sector.items(), key=lambda x: -x[1]):
        logger.info("  %-45s %s XOF", sector, f"{xof:,}")
    logger.info("Methodology: %s", wage_signal.methodology_note)

    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 03 — Econometric Signal 2: Sector Employment")
    logger.info(_DIV)

    growth_signal = econ.get_growth_signals()
    logger.info("Growth-flagged sectors: %s", growth_signal.growth_flagged_sectors)
    logger.info("Top sectors by employment share:")
    for s in growth_signal.sectors[:6]:
        logger.info("  %-45s %5.1f%%  [%s]  %s USD/mo",
                    s["sector"][:45], s["employment_share_pct"],
                    s["employment_status"], s.get("median_wage_usd", "n/a"))
    logger.info("Note: %s", growth_signal.methodology_note)

    # ──────────────────────────────────────────────────────────────
    # 3. Youth Dashboard
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 03 — Youth Dashboard")
    logger.info(_DIV)

    youth = generate_youth_dashboard(AKOSSIWA, risk, matches, wage_signal, growth_signal, config)
    logger.info("Profile summary  : %s", youth.profile_summary[:150] + "...")
    logger.info("Wage mirror:")
    logger.info("  Current  : %s XOF/month", f"{youth.wage_mirror['current_estimated_xof']:,}")
    logger.info("  Best opp : %s XOF/month", f"{youth.wage_mirror['best_opportunity_xof']:,}")
    logger.info("  Mult.    : ×%s", youth.wage_mirror['multiplier'])
    if youth.wage_mirror.get("ict_sector_median_xof"):
        logger.info("  ICT sect : %s XOF/month (aspirational signal)", f"{youth.wage_mirror['ict_sector_median_xof']:,}")
    logger.info("Next steps:")
    for i, step in enumerate(youth.next_steps, 1):
        logger.info("  %d. %s", i, step[:100])
    logger.info("Risk summary: band=%s, %%at-risk=%.0f%%",
                youth.risk_summary["overall_band"], youth.risk_summary["pct_at_risk"])

    # ──────────────────────────────────────────────────────────────
    # 4. Policymaker Dashboard
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info(_DIV)
    logger.info("MODULE 03 — Policymaker Dashboard (demo: 1 profile)")
    logger.info(_DIV)

    policy = generate_policymaker_dashboard(config, all_profiles=[AKOSSIWA])
    logger.info("Country           : %s", policy.country)
    logger.info("Youth unemployment: %.1f%%", policy.youth_unemployment)
    logger.info("NEET rate         : %.1f%%", policy.youth_neet)
    logger.info("Informal share    : %.1f%%", policy.informal_share)
    logger.info("Aggregate skills  : %s", policy.aggregate_skill_distribution)
    logger.info("Recommended areas (%d):", len(policy.recommended_program_areas))
    for p in policy.recommended_program_areas:
        logger.info("  • %s", p[:100])

    # ──────────────────────────────────────────────────────────────
    # Assertions
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Running assertions...")

    assert len(matches) >= 3, f"Expected ≥3 matches, got {len(matches)}"
    assert all(m.opportunity.realistic_for_youth for m in matches), "Non-realistic opportunity in results"
    assert wage_signal.wage_gap_multiplier >= 1.5, \
        f"Multiplier {wage_signal.wage_gap_multiplier} too low — wage gap signal not meaningful"

    # 2 econometric signals visible in youth dashboard
    assert "current_estimated_xof" in youth.wage_mirror, "Signal 1 missing from wage_mirror"
    assert "best_opportunity_xof" in youth.wage_mirror, "Signal 1b missing"
    assert len(youth.next_steps) >= 2, "Not enough next_steps"
    assert len(youth.transparency_notes) >= 2, "Not enough transparency notes"

    # Policymaker dashboard has aggregate fields
    assert policy.youth_unemployment > 0
    assert policy.informal_share > 50, "Informal share should be high for Bénin"
    assert len(policy.recommended_program_areas) >= 2

    # Growth signals populated
    assert len(growth_signal.growth_flagged_sectors) >= 1
    assert len(growth_signal.sectors) >= 5

    logger.info("")
    logger.info(_DIV)
    logger.info("ALL MODULE 03 ASSERTIONS PASSED")
    logger.info(_DIV)
