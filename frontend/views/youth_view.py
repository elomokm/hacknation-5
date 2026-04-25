"""Youth-facing view — the hero experience: skill input → economic mirror."""

import base64
import io
import json
import sys
from pathlib import Path
from uuid import uuid4

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.config_loader import get_active_config
from views.style import risk_badge

_DEMO_TEXT = (
    "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
    "depuis 4 ans dans mon atelier à Cotonou. J'ai appris HTML et un "
    "peu de Python sur YouTube. J'aide ma cousine à gérer son magasin "
    "de tissus, je tiens son inventaire sur Excel."
)


# ── Cached heavy objects (country-agnostic) ───────────────────────────────
@st.cache_resource
def _get_mapper():
    from module_01_skills.taxonomy_mapper import TaxonomyMapper
    return TaxonomyMapper()


@st.cache_resource
def _get_scorer():
    from module_02_risk.automation_scorer import AutomationScorer
    return AutomationScorer()


@st.cache_resource
def _get_finder():
    from module_02_risk.adjacent_skills import AdjacentSkillsFinder
    return AdjacentSkillsFinder()


# ── Country-scoped objects (recreated on country switch) ───────────────────
@st.cache_resource
def _get_matcher(country_code: str):
    from core.config_loader import load_config
    from module_03_opportunity.matcher import OpportunityMatcher
    return OpportunityMatcher(load_config(country_code))


@st.cache_resource
def _get_econ(country_code: str):
    from core.config_loader import load_config
    from module_03_opportunity.econometrics import EconometricSignals
    return EconometricSignals(load_config(country_code))


# ── Pipeline ───────────────────────────────────────────────────────────────
def _run_pipeline(description: str, edu: str, langs: list[str], name: str) -> None:
    """Run the full 3-module pipeline and store results in session_state."""
    from module_01_skills.extractor import extract_skills
    from module_01_skills.profile_generator import generate_profile
    from module_03_opportunity.dashboards import generate_youth_dashboard

    config = get_active_config()
    mapper = _get_mapper()
    scorer = _get_scorer()
    finder = _get_finder()
    matcher = _get_matcher(config.country_code)
    econ = _get_econ(config.country_code)

    progress = st.progress(0, text="Extracting skills from your description…")
    extracted = extract_skills(description)
    progress.progress(25, text="Mapping to ESCO taxonomy…")

    mapped = mapper.map_skills_batch(extracted)
    progress.progress(45, text="Building your standardized profile…")

    profile = generate_profile(
        user_id=str(uuid4()),
        user_name=name.strip() or "User",
        education_level=edu,
        languages=langs,
        extracted_skills=extracted,
        mapped_skills=mapped,
        config=config,
    )
    progress.progress(65, text="Assessing automation risk…")

    risk = scorer.score_profile(profile, config)
    progress.progress(75, text="Finding matching opportunities…")

    matches = matcher.match(profile, top_k=5)
    progress.progress(85, text="Computing econometric signals…")

    wage_signal = econ.get_wage_signals(profile)
    growth_signal = econ.get_growth_signals()
    progress.progress(95, text="Assembling your dashboard…")

    dashboard = generate_youth_dashboard(
        profile, risk, matches, wage_signal, growth_signal, config
    )
    progress.progress(100, text="Done!")
    progress.empty()

    st.session_state.update({
        "profile": profile,
        "risk": risk,
        "matches": matches,
        "wage_signal": wage_signal,
        "growth_signal": growth_signal,
        "dashboard": dashboard,
        "finder": finder,
        "scorer": scorer,
        "config_cc": config.country_code,
    })


# ── QR code helper ─────────────────────────────────────────────────────────
def _qr_base64(text: str) -> str:
    """Generate QR code PNG as base64 string."""
    import qrcode
    qr = qrcode.QRCode(version=2, box_size=5, border=2)
    qr.add_data(text[:900])  # QR capacity limit
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00D4AA", back_color="#0E1117")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Tab renderers ──────────────────────────────────────────────────────────
def _tab_profile(profile, config) -> None:
    st.markdown(f"### {profile.name}'s Skill Profile")
    st.caption(
        f"Education: **{profile.education.get('level')}** "
        f"(ISCED {profile.education.get('isced')}) · "
        f"Languages: {', '.join(profile.languages)}"
    )

    if not profile.skills:
        st.warning("No skills were mapped to the ESCO taxonomy. Try a more detailed description.")
        return

    for skill in profile.skills:
        conf = skill.raw_extraction.confidence
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{skill.esco_label}**")
                st.caption(f"ISCO: {', '.join(skill.isco_groups)} · Category: {skill.esco_category}")
            with c2:
                st.progress(conf, text=f"{conf:.0%}")
        st.markdown("---")

    # Portability block
    with st.expander("📦 Portability — ISCO codes"):
        isco_codes = profile.portability.get("isco_codes", [])
        st.markdown(
            f"**{profile.portability.get('esco_count', 0)} ESCO-mapped skills** · "
            f"{profile.portability.get('unmapped_skill_count', 0)} unmapped · "
            f"Standard: {profile.portability.get('standard', 'ESCO v1.2')}"
        )
        st.code(" · ".join(isco_codes) or "None", language=None)

    st.divider()

    # Download + QR
    profile_json = profile.model_dump_json(indent=2, by_alias=True)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ Download JSON-LD profile",
            data=profile_json,
            file_name=f"unmapped_{profile.profile_id[:8]}.json",
            mime="application/json",
        )
    with c2:
        if st.button("📷 Show QR code"):
            st.session_state["show_qr"] = not st.session_state.get("show_qr", False)

    if st.session_state.get("show_qr"):
        qr_b64 = _qr_base64(profile_json)
        st.image(
            f"data:image/png;base64,{qr_b64}",
            width=200,
            caption="Scan to access this profile JSON-LD",
        )


def _tab_risk(risk, profile, config) -> None:
    finder = st.session_state.get("finder")
    scorer = st.session_state.get("scorer")

    st.markdown("### Automation Risk Assessment")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Overall risk", risk.overall_risk_band.upper())
    with c2:
        st.metric("Avg probability", f"{risk.weighted_average_probability:.1%}")
    with c3:
        st.metric("Skills at risk", f"{risk.pct_skills_at_risk:.0%}")

    st.divider()

    for i, (skill, score) in enumerate(zip(profile.skills, risk.per_skill_scores)):
        badge = risk_badge(score.risk_band)
        adj = f"{score.adjusted_probability:.1%}" if score.adjusted_probability else "no data"

        with st.expander(f"{skill.esco_label}  —  {adj}", expanded=(i == 0)):
            st.markdown(badge, unsafe_allow_html=True)
            if score.matched_occupations:
                st.caption("Matched Frey-Osborne occupations: " + ", ".join(score.matched_occupations[:3]))
            if score.raw_frey_osborne:
                st.caption(
                    f"Raw F-O: {score.raw_frey_osborne:.3f} → "
                    f"LMIC-adjusted (×{score.lmic_adjustment_applied}): {score.adjusted_probability:.3f}"
                )

            # Adjacent alternatives for high-risk
            if score.risk_band in {"high", "critical"} and finder and scorer:
                alts = finder.find_durable_alternatives(skill, score, scorer, config, top_k=3)
                if alts:
                    st.markdown("**Lower-risk alternatives:**")
                    for alt in alts:
                        alt_adj = alt.automation_risk.adjusted_probability
                        st.markdown(
                            f"→ **{alt.esco_label}** — "
                            f"risk {alt_adj:.1%} ({alt.automation_risk.risk_band}) · "
                            f"proximity {alt.proximity_score:.2f}"
                        )
                        st.caption(alt.transition_rationale)

    st.divider()
    with st.expander("⚠️ Methodology & Limitations"):
        st.info(risk.methodology_note)
        for lim in risk.limitations:
            st.caption(f"• {lim}")


def _tab_opportunities(matches, config) -> None:
    usd = config.labor_data.usd_conversion_rate

    st.markdown("### Matched Opportunities")
    st.caption(
        f"Filtered to realistic_for_youth=True · "
        f"Sorted by profile fit · {config.country}"
    )

    if not matches:
        st.warning("No matching opportunities found. Try a more detailed description.")
        return

    for match in matches:
        o = match.opportunity
        wage_mid = (o.wage_range_xof[0] + o.wage_range_xof[1]) // 2

        _type_emoji = {
            "formal_employment": "🏢",
            "self_employment": "🛠️",
            "gig": "📱",
            "training_pathway": "🎓",
        }

        st.markdown(
            f"""<div class="opp-card">
            <div class="opp-title">{_type_emoji.get(o.type, "•")} {o.title_local}</div>
            <div class="opp-meta">
                {o.sector} · {o.geography} · {o.education_min}+
            </div>
            <div style="margin: 0.4rem 0; font-size:0.88rem; color:#B8BCC8;">
                {o.wage_range_xof[0]:,}–{o.wage_range_xof[1]:,} XOF/month
                ({o.wage_range_xof[0]//usd:,}–{o.wage_range_xof[1]//usd:,} USD)
            </div>
            <div class="opp-score-bar" style="width:{int(match.fit_score*100)}%"></div>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.expander(f"Details — fit score {match.fit_score:.0%}"):
            st.markdown(f"**{match.accessibility_note}**")
            if match.matched_isco:
                st.caption(f"ISCO overlap: {', '.join(match.matched_isco)}")
            if match.gap_education:
                st.warning(f"Education gap: {match.gap_education}")
            if match.gap_skills:
                st.caption(f"Skills to acquire: {len(match.gap_skills)} ESCO skills not yet in profile")
            if o.description:
                st.markdown(o.description)
            if o.training_url:
                st.markdown(f"🔗 [Training resource]({o.training_url})")


def _tab_mirror(dashboard, wage, config) -> None:
    """The hero moment — the economic mirror."""
    usd = config.labor_data.usd_conversion_rate

    st.markdown("## The Economic Mirror")
    st.caption("Real labor market data · ILOSTAT 2024 · Not aspirational — actual market medians")

    # Hero cards
    current = wage.current_estimated_xof
    best_opp = dashboard.wage_mirror.get("best_opportunity_xof", 0)
    ict = dashboard.wage_mirror.get("ict_sector_median_xof")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Today (informal)",
            f"{current:,} XOF",
            delta=f"{current // usd} USD/month",
            delta_color="off",
        )
    with c2:
        delta_pct = int((best_opp / max(current, 1) - 1) * 100) if best_opp > current else 0
        st.metric(
            "Best match for you",
            f"{best_opp:,} XOF",
            delta=f"+{delta_pct}%" if delta_pct > 0 else None,
        )
    with c3:
        if ict:
            ict_pct = int((ict / max(current, 1) - 1) * 100)
            st.metric(
                "ICT sector median",
                f"{ict:,} XOF",
                delta=f"+{ict_pct}%",
            )

    # Highlighted gap statement
    multiplier = dashboard.wage_mirror.get("multiplier", 1.0)
    if multiplier > 1.0:
        st.markdown(
            f"""<div class="wage-mirror-hero">
            <div class="wage-label">The gap</div>
            <div class="wage-value-primary">{wage.wage_gap_to_best_match_xof:,} XOF</div>
            <div class="wage-delta-up">×{multiplier:.1f} — the distance between today and your best match</div>
            <div class="data-note">Source: ILOSTAT 2024 · USD at {usd} XOF · Sector medians</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # Sector wage bar chart
    st.markdown("#### Wages by sector (XOF/month)")

    sectors = sorted(wage.formal_median_xof_by_sector.items(), key=lambda x: x[1])
    fig = go.Figure(go.Bar(
        x=[v for _, v in sectors],
        y=[k[:30] for k, _ in sectors],
        orientation="h",
        marker=dict(
            color=[
                "#00D4AA" if k == "Information and communication (ICT)" else
                "#FFA94D" if k == "Trade and commerce (informal)" else
                "#2A5298"
                for k, _ in sectors
            ]
        ),
        text=[f"{v:,}" for _, v in sectors],
        textposition="outside",
        textfont=dict(size=10, color="#B8BCC8"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="#B8BCC8", size=10)),
        margin=dict(l=0, r=80, t=10, b=10),
        height=max(240, len(sectors) * 30),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<p class="data-note">🟢 ICT median · 🟡 Your current estimated income '
        "(informal trade) · 🔵 Other sectors</p>",
        unsafe_allow_html=True,
    )
    st.caption(wage.methodology_note)

    st.divider()

    # Next steps
    st.markdown("#### Recommended next steps")
    for i, step in enumerate(dashboard.next_steps, 1):
        st.markdown(f"**{i}.** {step}")

    # Transparency
    with st.expander("⚠️ What this data doesn't show"):
        for note in dashboard.transparency_notes:
            st.caption(f"• {note}")


# ── Main entry point ───────────────────────────────────────────────────────
def render_youth_view() -> None:
    """Render the full youth-facing interface."""
    config = get_active_config()

    # Detect country switch → clear cache
    if st.session_state.get("config_cc") != config.country_code:
        for key in ["profile", "risk", "matches", "wage_signal", "growth_signal", "dashboard"]:
            st.session_state.pop(key, None)

    # ── Header ────────────────────────────────────────────────────
    st.markdown("## Tell us about yourself")
    st.caption(
        "Describe your experience in any language — French, English, Fon, Wolof. "
        "We'll extract your skills and show you your real economic options."
    )

    # ── Input form ────────────────────────────────────────────────
    with st.form("profile_form", clear_on_submit=False):
        description = st.text_area(
            "Your experience",
            value=_DEMO_TEXT,
            height=140,
            placeholder="Je répare des téléphones depuis 3 ans…",
            help="Write in your own words — any language, any format.",
        )
        c1, c2 = st.columns(2)
        with c1:
            edu = st.selectbox(
                "Education level",
                config.education_taxonomy.levels,
                index=min(2, len(config.education_taxonomy.levels) - 1),
            )
        with c2:
            langs = st.multiselect(
                "Languages spoken",
                config.ui.supported_languages,
                default=[config.ui.primary_language],
            )
        name = st.text_input("Your name (optional)", value="Akossiwa")
        submitted = st.form_submit_button(
            "🔍 Generate my profile", use_container_width=True
        )

    if submitted:
        if not description.strip():
            st.error("Please describe at least one skill or experience.")
        else:
            with st.container():
                _run_pipeline(description, edu, langs, name)

    # ── Results tabs ──────────────────────────────────────────────
    if "dashboard" in st.session_state and "profile" in st.session_state:
        profile = st.session_state["profile"]
        risk = st.session_state["risk"]
        matches = st.session_state["matches"]
        wage_signal = st.session_state["wage_signal"]
        dashboard = st.session_state["dashboard"]

        st.divider()
        st.markdown(f"*{dashboard.profile_summary}*")
        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs(
            ["👤 Profile", "⚠️ Risk", "🎯 Opportunities", "💰 Mirror"]
        )
        with tab1:
            _tab_profile(profile, config)
        with tab2:
            _tab_risk(risk, profile, config)
        with tab3:
            _tab_opportunities(matches, config)
        with tab4:
            _tab_mirror(dashboard, wage_signal, config)

        # Footer
        st.divider()
        st.markdown(
            '<p class="data-note" style="text-align:center">'
            "Profile portable across borders · ISCO-08 standardized · ESCO v1.2 mapped · "
            f"Generated by UNMAPPED · {config.country}"
            "</p>",
            unsafe_allow_html=True,
        )
