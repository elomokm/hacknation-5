"""Youth-facing view — the hero experience: skill input → economic mirror.

Now consumes the UNMAPPED API via HTTP (no direct module imports for the pipeline).
"""

import base64
import io
import json
import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.config_loader import get_active_config
from core.models import (
    AdjacentSkill,
    OpportunityMatch,
    RiskAssessment,
    SectorGrowthSignal,
    StandardizedProfile,
    WageSignal,
    YouthDashboard,
)
from views.style import risk_badge

API_BASE = os.getenv("UNMAPPED_API_URL", "http://localhost:8000/api")

_DEMO_TEXT = (
    "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
    "depuis 4 ans dans mon atelier à Cotonou. J'ai appris HTML et un "
    "peu de Python sur YouTube. J'aide ma cousine à gérer son magasin "
    "de tissus, je tiens son inventaire sur Excel."
)


# ── API client helpers ─────────────────────────────────────────────────────
def _api_post(path: str, body: dict, timeout: int = 60):
    """POST to UNMAPPED API; raise readable error on failure."""
    r = requests.post(f"{API_BASE}{path}", json=body, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"API {path} returned {r.status_code}: {r.text[:200]}")
    return r.json()


def _api_get(path: str, timeout: int = 30):
    r = requests.get(f"{API_BASE}{path}", timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"API {path} returned {r.status_code}: {r.text[:200]}")
    return r.json()


def _check_api_alive() -> bool:
    """Return True if the API responds to /health within 2 seconds."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ── Pipeline ───────────────────────────────────────────────────────────────
def _run_pipeline(description: str, edu: str, langs: list[str], name: str) -> None:
    """Call the UNMAPPED API and store results in session_state."""
    config = get_active_config()
    cc = config.country_code

    progress = st.progress(0, text="Generating your profile (calling UNMAPPED API)…")
    profile = _api_post("/profile/generate", {
        "user_name": name.strip() or "User",
        "text": description,
        "education_level": edu,
        "languages": langs,
        "country_code": cc,
    })
    profile_id = profile["profile_id"]
    progress.progress(45, text="Assessing automation risk…")

    risk_resp = _api_post("/risk/assess", {
        "profile_id": profile_id,
        "country_code": cc,
        "include_adjacent": True,
    })
    progress.progress(70, text="Matching opportunities…")

    match_resp = _api_post("/opportunities/match", {
        "profile_id": profile_id,
        "country_code": cc,
        "top_k": 5,
    })
    progress.progress(90, text="Assembling dashboard…")

    dashboard = _api_get(f"/opportunities/{cc}/dashboard/youth?profile_id={profile_id}")

    progress.progress(100, text="Done!")
    progress.empty()

    # Parse dict responses back into Pydantic models so the tab renderers
    # work uniformly (whether data came from API or local pipeline).
    st.session_state.update({
        "profile": StandardizedProfile.model_validate(profile),
        "risk": RiskAssessment.model_validate(risk_resp["assessment"]),
        "adjacent": {
            esco_id: [AdjacentSkill.model_validate(a) for a in alts]
            for esco_id, alts in risk_resp["adjacent_skills"].items()
        },
        "matches": [OpportunityMatch.model_validate(m) for m in match_resp["matches"]],
        "wage_signal": WageSignal.model_validate(match_resp["wage_signal"]),
        "growth_signal": SectorGrowthSignal.model_validate(match_resp["growth_signal"]),
        "dashboard": YouthDashboard.model_validate(dashboard),
        "config_cc": cc,
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
    with st.expander("Portability"):
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
            "Download JSON-LD profile",
            data=profile_json,
            file_name=f"unmapped_{profile.profile_id[:8]}.json",
            mime="application/json",
        )
    with c2:
        if st.button("Show QR code"):
            st.session_state["show_qr"] = not st.session_state.get("show_qr", False)

    if st.session_state.get("show_qr"):
        qr_b64 = _qr_base64(profile_json)
        st.image(
            f"data:image/png;base64,{qr_b64}",
            width=200,
            caption="Scan to access this profile JSON-LD",
        )


def _tab_risk(risk, profile, config) -> None:
    adjacent = st.session_state.get("adjacent", {})

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

            # Adjacent alternatives for high-risk (precomputed via /risk/assess)
            if score.risk_band in {"high", "critical"}:
                alts = adjacent.get(skill.esco_id, [])
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
    with st.expander("Methodology and limitations"):
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

        _type_label = {
            "formal_employment": "Formal",
            "self_employment": "Self",
            "gig": "Gig",
            "training_pathway": "Training",
        }

        st.markdown(
            f"""<div class="opp-card">
            <div class="opp-title">[{_type_label.get(o.type, o.type)}] {o.title_local}</div>
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
                st.markdown(f"[Training resource]({o.training_url})")


def _tab_mirror(dashboard, wage, growth, matches, config) -> None:
    """The hero moment — the economic mirror.

    Surfaces both econometric signals (wage + employment share) and
    explicit realistic vs aspirational gap framing.
    """
    usd = config.labor_data.usd_conversion_rate

    st.markdown("## The Economic Mirror")
    st.caption("Real labor market data · ILOSTAT 2024 · Not aspirational — actual market medians")

    # ── Hero cards ───────────────────────────────────────────────
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

    # FIX 3 — Explain the trade-off behind "Best match for you"
    if matches:
        top = matches[0].opportunity
        top_median = (top.wage_range_xof[0] + top.wage_range_xof[1]) // 2
        top_fit = matches[0].fit_score
        # Find a higher-paying alternative ranked lower
        higher_paying = next(
            (m for m in matches[1:]
             if (m.opportunity.wage_range_xof[0] + m.opportunity.wage_range_xof[1]) // 2
                > top_median * 1.3),
            None,
        )
        caption_lines = [
            f"**Top-fit match:** {top.title_local} "
            f"({top_fit:.0%} profile fit, median {top_median:,} XOF)."
        ]
        if higher_paying:
            hp = higher_paying.opportunity
            caption_lines.append(
                f"Higher-paying option exists ({hp.title_local}: "
                f"{hp.wage_range_xof[0]:,}–{hp.wage_range_xof[1]:,} XOF, "
                f"fit {higher_paying.fit_score:.0%}) — trade-off between fit and wage."
            )
        st.caption(" ".join(caption_lines))

    # ── FIX 2 — Two gap cards: realistic vs aspirational ─────────
    if best_opp > current or (ict and ict > current):
        col_gap1, col_gap2 = st.columns(2)
        with col_gap1:
            r_gap = best_opp - current
            r_mult = best_opp / max(current, 1)
            st.markdown(
                f"""<div class="gap-card realistic">
                <div class="gap-label">Realistic gap</div>
                <div class="gap-value">+{r_gap:,} XOF</div>
                <div class="gap-meta">×{r_mult:.1f} — best accessible opportunity</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_gap2:
            if ict:
                a_gap = ict - current
                a_mult = ict / max(current, 1)
                st.markdown(
                    f"""<div class="gap-card aspirational">
                    <div class="gap-label">Aspirational gap</div>
                    <div class="gap-value">+{a_gap:,} XOF</div>
                    <div class="gap-meta">×{a_mult:.1f} — ICT sector median</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    st.markdown(
        f'<p class="data-note">Source: ILOSTAT 2024 · USD at {usd} XOF · Sector medians</p>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Signal 1 — Wages by sector ───────────────────────────────
    st.markdown("#### Wages by sector (XOF/month)")
    st.caption("Signal 1: median wage per sector.")

    sectors = sorted(wage.formal_median_xof_by_sector.items(), key=lambda x: x[1])
    fig_w = go.Figure(go.Bar(
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
    fig_w.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="#B8BCC8", size=10)),
        margin=dict(l=0, r=80, t=10, b=10),
        height=max(240, len(sectors) * 30),
    )
    st.plotly_chart(fig_w, use_container_width=True)

    st.markdown(
        '<p class="data-note">Green = ICT median · Orange = your current estimated '
        "income (informal trade) · Blue = other sectors</p>",
        unsafe_allow_html=True,
    )
    st.caption(wage.methodology_note)

    st.divider()

    # ── FIX 1 — Signal 2 — Employment share by sector ────────────
    st.subheader("Where the jobs are")
    st.caption(
        "Real employment distribution by sector — ILOSTAT 2024. "
        "Signal 2: sector employment share."
    )

    emp_sectors = sorted(growth.sectors, key=lambda s: s["employment_share_pct"])
    flagged = set(growth.growth_flagged_sectors)

    fig_e = go.Figure(go.Bar(
        x=[s["employment_share_pct"] for s in emp_sectors],
        y=[s["sector"][:30] for s in emp_sectors],
        orientation="h",
        marker_color=[
            "#00D4AA" if s["sector"] in flagged else "#2A5298"
            for s in emp_sectors
        ],
        text=[f"{s['employment_share_pct']:.1f}%" for s in emp_sectors],
        textposition="outside",
        textfont=dict(size=10, color="#B8BCC8"),
    ))
    fig_e.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="#B8BCC8", size=10)),
        margin=dict(l=0, r=60, t=10, b=10),
        height=max(240, len(emp_sectors) * 30),
    )
    st.plotly_chart(fig_e, use_container_width=True)

    # Build the structural-gap caption from real data
    agri = next((s for s in growth.sectors if "Agriculture" in s["sector"]), None)
    ict_emp = next((s for s in growth.sectors if "ICT" in s["sector"]), None)
    if agri and ict_emp:
        st.markdown(
            f"**The structural gap**: agriculture employs "
            f"{agri['employment_share_pct']:.0f}% of {config.country} but pays the least. "
            f"ICT pays the most but employs less than {ict_emp['employment_share_pct']:.1f}%. "
            f"This is the challenge UNMAPPED helps youth navigate."
        )

    st.divider()

    # ── Next steps ───────────────────────────────────────────────
    st.markdown("#### Recommended next steps")
    for i, step in enumerate(dashboard.next_steps, 1):
        st.markdown(f"**{i}.** {step}")

    # Transparency
    with st.expander("What this data doesn't show"):
        for note in dashboard.transparency_notes:
            st.caption(f"• {note}")


# ── Main entry point ───────────────────────────────────────────────────────
def render_youth_view() -> None:
    """Render the full youth-facing interface."""
    config = get_active_config()

    # Detect country switch → clear cache
    if st.session_state.get("config_cc") != config.country_code:
        for key in ["profile", "risk", "adjacent", "matches", "wage_signal", "growth_signal", "dashboard"]:
            st.session_state.pop(key, None)

    # API health check
    if not _check_api_alive():
        st.error(
            f"UNMAPPED API not reachable at `{API_BASE}`. "
            f"Start the API with `make api` in another terminal."
        )
        return

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
            "Generate my profile", use_container_width=True
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
        growth_signal = st.session_state["growth_signal"]
        dashboard = st.session_state["dashboard"]

        st.divider()
        st.markdown(f"*{dashboard.profile_summary}*")
        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Profile", "Risk", "Opportunities", "Mirror"]
        )
        with tab1:
            _tab_profile(profile, config)
        with tab2:
            _tab_risk(risk, profile, config)
        with tab3:
            _tab_opportunities(matches, config)
        with tab4:
            _tab_mirror(dashboard, wage_signal, growth_signal, matches, config)

        # Footer
        st.divider()
        st.markdown(
            '<p class="data-note" style="text-align:center">'
            "Profile portable across borders · ISCO-08 standardized · ESCO v1.2 mapped · "
            f"Generated by UNMAPPED · {config.country}"
            "</p>",
            unsafe_allow_html=True,
        )
