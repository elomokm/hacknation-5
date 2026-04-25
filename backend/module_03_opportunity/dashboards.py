"""Module 03 — Dashboard assembler: combines all 3 modules into dual interface.

One optional LLM call for profile_summary (reuses existing if available).
"""

import logging
from collections import Counter
from pathlib import Path

from core.models import (
    CountryConfig,
    OpportunityMatch,
    PolicymakerDashboard,
    RiskAssessment,
    SectorGrowthSignal,
    StandardizedProfile,
    WageSignal,
    YouthDashboard,
)

logger = logging.getLogger(__name__)


def generate_youth_dashboard(
    profile: StandardizedProfile,
    risk_assessment: RiskAssessment,
    matches: list[OpportunityMatch],
    wage_signal: WageSignal,
    growth_signal: SectorGrowthSignal,
    config: CountryConfig,
) -> YouthDashboard:
    """Assemble the youth-facing dashboard — the 'economic mirror'."""

    # Profile summary: reuse existing if available, else build deterministically
    summary = profile.human_readable_summary or _build_basic_summary(profile, config)

    top_3 = matches[:3]

    # Wage mirror — the key "economic mirror" signal
    best_opp_xof = (
        top_3[0].wage_delta.get("opportunity_median_xof", 0) if top_3 else 0
    )
    wage_mirror = {
        "current_estimated_xof": wage_signal.current_estimated_xof,
        "current_estimated_usd": wage_signal.current_estimated_usd,
        "best_opportunity_xof": best_opp_xof,
        "best_opportunity_usd": round(
            best_opp_xof / config.labor_data.usd_conversion_rate
        ),
        "multiplier": round(
            best_opp_xof / max(wage_signal.current_estimated_xof, 1), 2
        ),
        "ict_sector_median_xof": wage_signal.formal_median_xof_by_sector.get(
            "Information and communication (ICT)", None
        ),
        "source": "ILOSTAT 2024",
    }

    # Risk summary
    high_risk = [
        s for s in risk_assessment.per_skill_scores
        if s.risk_band in {"high", "critical"}
    ]
    risk_summary = {
        "overall_band": risk_assessment.overall_risk_band,
        "pct_at_risk": round(risk_assessment.pct_skills_at_risk * 100, 1),
        "high_risk_skills": [
            {
                "label": s.esco_label,
                "band": s.risk_band,
                "adjusted_probability": s.adjusted_probability,
            }
            for s in high_risk
        ],
        "methodology": risk_assessment.methodology_note,
    }

    # Next steps (3 concrete, data-driven actions)
    next_steps: list[str] = []

    if top_3:
        best = top_3[0]
        step1 = (
            f"Explore: '{best.opportunity.title_local}' — "
            f"potential income {best.opportunity.wage_range_xof[0]:,}–"
            f"{best.opportunity.wage_range_xof[1]:,} XOF/month "
            f"({best.opportunity.geography})."
        )
        next_steps.append(step1)

    # Training pathways
    training = [m for m in matches if m.opportunity.type == "training_pathway"]
    if training:
        t = training[0]
        url_part = f" → {t.opportunity.training_url}" if t.opportunity.training_url else ""
        next_steps.append(
            f"Formation disponible: '{t.opportunity.title_local}'"
            f"{url_part} — accessible avec votre niveau actuel."
        )

    if high_risk:
        hr = high_risk[0]
        next_steps.append(
            f"Compétence à risque élevé: '{hr.esco_label}' "
            f"(risque ajusté {hr.adjusted_probability:.0%}). "
            f"Diversifier vers des secteurs numériques ou à faible automatisation."
        )

    if len(next_steps) < 3:
        next_steps.append(
            f"Formaliser vos compétences: un certificat reconnu peut multiplier "
            f"votre revenu estimé de {wage_signal.current_estimated_xof:,} XOF "
            f"jusqu'à {wage_signal.wage_gap_to_best_match_xof + wage_signal.current_estimated_xof:,} XOF/mois."
        )

    # Transparency notes
    transparency = [
        "Les scores de risque proviennent de Frey-Osborne (2017), calibrés pour le contexte LMIC.",
        "Les salaires sont des médianes sectorielles — les salaires individuels varient.",
        "Le matching est basé sur les codes ISCO, pas sur une évaluation de poste.",
        "Ce profil ne remplace pas un conseiller d'orientation professionnel.",
    ]

    return YouthDashboard(
        profile_summary=summary,
        top_3_opportunities=top_3,
        wage_mirror=wage_mirror,
        risk_summary=risk_summary,
        next_steps=next_steps[:3],
        transparency_notes=transparency,
    )


def generate_policymaker_dashboard(
    config: CountryConfig,
    all_profiles: list[StandardizedProfile] | None = None,
) -> PolicymakerDashboard:
    """Assemble the policymaker-facing aggregate dashboard."""
    from core.config_loader import load_config
    from module_03_opportunity.econometrics import EconometricSignals

    profiles = all_profiles or []
    econ = EconometricSignals(config)
    growth = econ.get_growth_signals()

    # Aggregate skill distribution across all profiles
    skill_cats: Counter = Counter()
    isco_dist: Counter = Counter()
    for p in profiles:
        for s in p.skills:
            skill_cats[s.esco_category] += 1
            for code in s.isco_groups:
                isco_dist[code] += 1

    # Automation risk aggregate (placeholder when no profiles)
    auto_aggregate = {
        "profiles_analysed": len(profiles),
        "note": "Aggregate risk computed per-profile when data available.",
    }

    # Skill gaps by sector: which sectors are hiring vs what profiles supply
    growth_sectors = growth.growth_flagged_sectors
    skill_gaps: list[dict] = []
    for sector in growth_sectors:
        skill_gaps.append({
            "sector": sector,
            "flag": "high_value",
            "isco_needed": ["25", "21", "33"],
            "gap_note": f"High-value sector — ICT/digital skills most needed.",
        })

    # Recommended program areas
    programs: list[str] = [
        f"Digital skills training (ICT sector wage: "
        f"{econ._wage_by_sector.get('Information and communication (ICT)', 0):,} XOF/month "
        f"vs informal trade {econ._wage_by_sector.get('Trade and commerce (informal)', 0):,} XOF).",
        f"TVET certification in electronics/maintenance — aligns with ISCO 74 demand.",
        f"Financial literacy and mobile money training — leverages existing commerce skills.",
        f"Agricultural value-chain training — {config.country}'s {[e.share_pct for e in econ._labor.employment_by_sector if 'Agriculture' in e.sector[:11]][0] if [e for e in econ._labor.employment_by_sector if 'Agriculture' in e.sector[:11]] else 0:.0f}% of workforce in agriculture.",
    ]

    return PolicymakerDashboard(
        country=config.country,
        aggregate_skill_distribution=dict(skill_cats),
        aggregate_isco_distribution=dict(isco_dist),
        youth_unemployment=econ._labor.youth_unemployment_rate,
        youth_neet=getattr(econ._labor, "youth_neet_rate", 0.0),
        informal_share=econ._labor.informal_employment_share,
        automation_risk_aggregate=auto_aggregate,
        skill_gaps_by_sector=skill_gaps,
        recommended_program_areas=programs,
    )


def _build_basic_summary(profile: StandardizedProfile, config: CountryConfig) -> str:
    """Deterministic fallback summary when LLM summary is unavailable."""
    skill_labels = [s.esco_label for s in profile.skills[:4]]
    skills_str = ", ".join(skill_labels) if skill_labels else "compétences non encore cartographiées"
    return (
        f"{profile.name} présente un profil avec {len(profile.skills)} compétence(s) "
        f"identifiée(s) : {skills_str}. "
        f"Niveau d'éducation : {profile.education.get('level', 'non renseigné')} "
        f"(ISCED {profile.education.get('isced', '?')}). "
        f"Pays : {config.country}."
    )
