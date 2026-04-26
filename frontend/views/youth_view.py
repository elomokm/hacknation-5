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
from views.i18n import t
from views.skill_graph import render_skill_graph
from views.style import risk_badge

# API URL resolution: env var first (local dev), then Streamlit secrets (Cloud), then localhost.
def _resolve_api_url() -> str:
    if os.getenv("UNMAPPED_API_URL"):
        return os.environ["UNMAPPED_API_URL"]
    try:
        # st.secrets only exists when running under Streamlit
        if "UNMAPPED_API_URL" in st.secrets:
            return st.secrets["UNMAPPED_API_URL"]
    except Exception:
        pass
    return "http://localhost:8000/api"


API_BASE = _resolve_api_url()

_DEMO_TEXT = (
    "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
    "depuis 4 ans dans mon atelier à Cotonou. J'ai appris HTML et un "
    "peu de Python sur YouTube. J'aide ma cousine à gérer son magasin "
    "de tissus, je tiens son inventaire sur Excel."
)

# Demo personas — one-click prefill that switches country + form fields.
# Order matches the brief's regional progression: West Africa × 3, then South Asia.
_PERSONAS: list[dict] = [
    {
        "country": "BEN",
        "flag": "🇧🇯",
        "name": "Akossiwa",
        "age": 22,
        "city": "Cotonou",
        "tagline": "Phone repair · Excel inventory · HTML basics",
        "education": "BEPC",
        "languages": ["fr", "fon"],
        "text": (
            "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
            "depuis 4 ans dans mon atelier à Cotonou. J'ai appris HTML et un "
            "peu de Python sur YouTube. J'aide ma cousine à gérer son magasin "
            "de tissus, je tiens son inventaire sur Excel."
        ),
    },
    {
        "country": "SEN",
        "flag": "🇸🇳",
        "name": "Mamadou",
        "age": 24,
        "city": "Thiès",
        "tagline": "Cash crops · Tractor · Weekly market sales",
        "education": "BFEM",
        "languages": ["fr", "wo"],
        "text": (
            "Je m'appelle Mamadou. J'ai un BFEM. Je travaille avec mon père "
            "sur une ferme près de Thiès depuis 6 ans. On cultive du mil et "
            "des arachides. Je conduis le tracteur. Je vends au marché chaque semaine."
        ),
    },
    {
        "country": "GHA",
        "flag": "🇬🇭",
        "name": "Amara",
        "age": 24,
        "city": "Kumasi",
        "tagline": "Carpentry apprentice · Furniture · Roadside sales",
        "education": "WASSCE",
        "languages": ["en", "tw"],
        "text": (
            "I'm Amara, 24, from Kumasi. I've been a carpentry apprentice for "
            "3 years in my uncle's workshop. We build furniture from local wood "
            "— chairs, tables, doors. I'm learning to use power tools. I sometimes "
            "help with sales at our roadside shop."
        ),
    },
    {
        "country": "BGD",
        "flag": "🇧🇩",
        "name": "Rashida",
        "age": 23,
        "city": "Khulna",
        "tagline": "Rice farming · Home tailoring · Village sales",
        "education": "SSC",
        "languages": ["bn", "en"],
        "text": (
            "I'm Rashida, 23, from Khulna. I help my family with rice farming "
            "and run a small home tailoring business. I sew kameez and lehenga "
            "for women in my village. I learned tailoring from my mother and "
            "basic English from school."
        ),
    },
]


_FLAG_BY_CC = {p["country"]: p["flag"] for p in _PERSONAS}


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
    """Return True if the API responds to /health.

    Generous timeout so a Render free-tier cold start (typically 30-50s) wakes
    the dyno on the first request instead of failing fast.
    """
    try:
        r = requests.get(f"{API_BASE}/health", timeout=60)
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
    """Human-readable profile view: cards per ESCO category + collapsible graph.

    Designed so Akossiwa understands her own profile in one glance —
    not buried in a graph that requires hovering every node.
    """
    from collections import defaultdict
    from views.skill_graph import _CATEGORY_COLOR, _DEFAULT_COLOR

    # ── Hero header ──────────────────────────────────────────────
    st.markdown(f"### {t('profile.title', name=profile.name)}")
    st.caption(t(
        "profile.education_lang",
        level=profile.education.get("level"),
        isced=profile.education.get("isced"),
        langs=", ".join(profile.languages),
    ))

    if not profile.skills:
        st.warning(t("profile.no_skills_warn"))
        return

    # ── Standardization summary banner ───────────────────────────
    isco_codes = profile.portability.get("isco_codes", [])
    n_mapped = profile.portability.get("esco_count", 0)
    n_unmapped = profile.portability.get("unmapped_skill_count", 0)
    n_total = n_mapped + n_unmapped

    isco_inline = " ".join(isco_codes) or "—"
    summary_html = (
        '<div class="profile-summary-banner">'
        f'<div class="profile-summary-stat"><span class="profile-summary-num">{n_mapped}</span>'
        f'<span class="profile-summary-label">{t("profile.summary_mapped")}</span></div>'
        '<div class="profile-summary-divider">·</div>'
        f'<div class="profile-summary-stat"><span class="profile-summary-num">{n_unmapped}</span>'
        f'<span class="profile-summary-label">{t("profile.summary_unmapped")}</span></div>'
        '<div class="profile-summary-divider">·</div>'
        f'<div class="profile-summary-meta">ESCO v1.2 · ISCO-08 codes: <code>{isco_inline}</code></div>'
        '</div>'
    )
    st.markdown(summary_html, unsafe_allow_html=True)

    # ── Download JSON-LD (compact) ───────────────────────────────
    profile_json = profile.model_dump_json(indent=2, by_alias=True)
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        st.download_button(
            "↓ JSON-LD",
            data=profile_json,
            file_name=f"unmapped_{profile.profile_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
            help=t("profile.download"),
        )
    with c2:
        if st.button("◧ QR code", use_container_width=True, help=t("profile.show_qr")):
            st.session_state["show_qr"] = not st.session_state.get("show_qr", False)

    if st.session_state.get("show_qr"):
        qr_b64 = _qr_base64(profile_json)
        st.image(
            f"data:image/png;base64,{qr_b64}",
            width=160,
            caption=t("profile.qr_caption"),
        )

    st.divider()

    # ── Cards grouped by ESCO category ───────────────────────────
    adjacent = st.session_state.get("adjacent", {})
    skills_by_cat: dict[str, list] = defaultdict(list)
    for skill in profile.skills:
        skills_by_cat[skill.esco_category].append(skill)

    # Order categories by number of skills (most populated first)
    ordered_cats = sorted(
        skills_by_cat.items(),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )

    for category, skills in ordered_cats:
        color = _CATEGORY_COLOR.get(category, _DEFAULT_COLOR)

        # Inner skills HTML — each on a single line to avoid markdown code-block trap
        skills_html_parts: list[str] = []
        for skill in skills:
            conf_pct = f"{int(skill.raw_extraction.confidence * 100)}%"
            isco = ", ".join(skill.isco_groups)
            conf_label = t("profile.confidence", pct=conf_pct)
            skills_html_parts.append(
                f'<div class="cat-skill">'
                f'<div class="cat-skill-label">{skill.esco_label}</div>'
                f'<div class="cat-skill-meta">ISCO {isco} · {conf_label}</div>'
                f'</div>'
            )

        # Combine adjacents across all skills in this category
        all_adjacent = []
        seen_adj_ids: set[str] = set()
        for skill in skills:
            for alt in adjacent.get(skill.esco_id, []):
                if alt.esco_id not in seen_adj_ids:
                    all_adjacent.append(alt)
                    seen_adj_ids.add(alt.esco_id)
        all_adjacent = all_adjacent[:3]

        if all_adjacent:
            adj_items = "".join(
                f"<li><strong>{a.esco_label}</strong>"
                f"<span class='cat-adj-meta'> · {a.esco_category} · "
                f"risk {a.automation_risk.risk_band}</span></li>"
                for a in all_adjacent
            )
            adj_block = (
                '<div class="cat-adj-section">'
                f'<div class="cat-adj-title">→ {t("profile.adjacent_label")}</div>'
                f'<ul class="cat-adj-list">{adj_items}</ul>'
                '</div>'
            )
        else:
            adj_block = ""

        skill_count_label = f'{len(skills)} skill{"s" if len(skills) > 1 else ""}'
        card_html = (
            f'<div class="category-card" style="border-left-color: {color};">'
            '<div class="cat-header">'
            f'<span class="cat-dot" style="background:{color};"></span>'
            f'<span class="cat-name">{category.upper()}</span>'
            f'<span class="cat-count">{skill_count_label}</span>'
            '</div>'
            f'<div class="cat-skills">{"".join(skills_html_parts)}</div>'
            f'{adj_block}'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    st.divider()

    # ── Interactive graph (collapsible — visual detail, not the hero) ──
    with st.expander(t("profile.see_graph"), expanded=False):
        graph_html = render_skill_graph(profile, adjacent, max_neighbors=2)
        if graph_html:
            import streamlit.components.v1 as components
            components.html(graph_html, height=520, scrolling=False)
            st.caption(t("profile.graph_legend"))
        else:
            st.info(t("profile.graph_unavailable"))


def _tab_risk(risk, profile, config) -> None:
    adjacent = st.session_state.get("adjacent", {})

    st.markdown(f"### {t('risk.title')}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("risk.overall"), risk.overall_risk_band.upper())
    with c2:
        st.metric(t("risk.avg_prob"), f"{risk.weighted_average_probability:.1%}")
    with c3:
        st.metric(t("risk.pct_at_risk"), f"{risk.pct_skills_at_risk:.0%}")

    st.divider()

    for i, (skill, score) in enumerate(zip(profile.skills, risk.per_skill_scores)):
        badge = risk_badge(score.risk_band)
        adj = f"{score.adjusted_probability:.1%}" if score.adjusted_probability else "no data"

        with st.expander(f"{skill.esco_label}  —  {adj}", expanded=(i == 0)):
            st.markdown(badge, unsafe_allow_html=True)
            if score.matched_occupations:
                st.caption(t("risk.matched_occupations") + ", ".join(score.matched_occupations[:3]))
            if score.raw_frey_osborne:
                st.caption(
                    f"Raw F-O: {score.raw_frey_osborne:.3f} → "
                    f"LMIC-adjusted (×{score.lmic_adjustment_applied}): {score.adjusted_probability:.3f}"
                )

            # Adjacent alternatives for high-risk (precomputed via /risk/assess)
            if score.risk_band in {"high", "critical"}:
                alts = adjacent.get(skill.esco_id, [])
                if alts:
                    st.markdown(f"**{t('risk.alternatives_label')}**")
                    for alt in alts:
                        alt_adj = alt.automation_risk.adjusted_probability
                        st.markdown(
                            f"→ **{alt.esco_label}** — "
                            f"risk {alt_adj:.1%} ({alt.automation_risk.risk_band}) · "
                            f"proximity {alt.proximity_score:.2f}"
                        )
                        st.caption(alt.transition_rationale)

    st.divider()
    with st.expander(t("risk.methodology")):
        st.info(risk.methodology_note)
        for lim in risk.limitations:
            st.caption(f"• {lim}")


def _tab_opportunities(matches, config) -> None:
    usd = config.labor_data.usd_conversion_rate

    st.markdown(f"### {t('opp.title')}")
    st.caption(t("opp.caption", country=config.country))

    if not matches:
        st.warning(t("opp.empty_warn"))
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

        with st.expander(t("opp.details", score=f"{match.fit_score:.0%}")):
            st.markdown(f"**{match.accessibility_note}**")
            if match.matched_isco:
                st.caption(f"ISCO: {', '.join(match.matched_isco)}")
            if match.gap_education:
                st.warning(t("opp.education_gap", gap=match.gap_education))
            if match.gap_skills:
                st.caption(t("opp.skills_to_acquire", n=len(match.gap_skills)))
            if o.description:
                st.markdown(o.description)
            if o.training_url:
                st.markdown(f"[{t('opp.training_resource')}]({o.training_url})")


def _tab_mirror(dashboard, wage, growth, matches, config) -> None:
    """The hero moment — the economic mirror.

    Surfaces both econometric signals (wage + employment share) and
    explicit realistic vs aspirational gap framing.
    """
    usd = config.labor_data.usd_conversion_rate
    currency = config.labor_data.currency

    st.markdown(f"## {t('mirror.title')}")
    st.caption(t("mirror.caption"))

    # ── Hero cards ───────────────────────────────────────────────
    current = wage.current_estimated_xof
    best_opp = dashboard.wage_mirror.get("best_opportunity_xof", 0)
    ict = dashboard.wage_mirror.get("ict_sector_median_xof")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            t("mirror.today"),
            f"{current:,} {currency}",
            delta=f"{current // usd} USD/month",
            delta_color="off",
        )
    with c2:
        delta_pct = int((best_opp / max(current, 1) - 1) * 100) if best_opp > current else 0
        st.metric(
            t("mirror.best_match"),
            f"{best_opp:,} {currency}",
            delta=f"+{delta_pct}%" if delta_pct > 0 else None,
        )
    with c3:
        if ict:
            ict_pct = int((ict / max(current, 1) - 1) * 100)
            st.metric(
                t("mirror.ict_median"),
                f"{ict:,} {currency}",
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
                <div class="gap-label">{t("mirror.realistic_gap")}</div>
                <div class="gap-value">+{r_gap:,} {currency}</div>
                <div class="gap-meta">{t("mirror.realistic_meta", mult=f"{r_mult:.1f}")}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_gap2:
            if ict:
                a_gap = ict - current
                a_mult = ict / max(current, 1)
                st.markdown(
                    f"""<div class="gap-card aspirational">
                    <div class="gap-label">{t("mirror.aspirational_gap")}</div>
                    <div class="gap-value">+{a_gap:,} {currency}</div>
                    <div class="gap-meta">{t("mirror.aspirational_meta", mult=f"{a_mult:.1f}")}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    st.markdown(
        f'<p class="data-note">Source: ILOSTAT 2024 · USD at {usd} {currency} · Sector medians</p>',
        unsafe_allow_html=True,
    )

    # ── Recommended next steps — promoted to top of Mirror, callout style ──
    if dashboard.next_steps:
        steps_html = "".join(
            f'<div class="next-step-item">'
            f'<span class="next-step-num">{i}</span>'
            f'<span class="next-step-text">{step}</span>'
            f'</div>'
            for i, step in enumerate(dashboard.next_steps, 1)
        )
        st.markdown(
            f"""<div class="next-steps-callout">
                <div class="next-steps-title">{t("mirror.next_steps_title")}</div>
                {steps_html}
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Signal 1 — Wages by sector ───────────────────────────────
    st.markdown(f"#### {t('mirror.wages_title', currency=currency)}")
    st.caption(t("mirror.wages_caption"))

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
    st.subheader(t("mirror.jobs_title"))
    st.caption(t("mirror.jobs_caption"))

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

    # Transparency
    with st.expander(t("mirror.transparency_expander")):
        for note in dashboard.transparency_notes:
            st.caption(f"• {note}")


# ── Country banner + persona buttons ───────────────────────────────────────
def _render_country_banner(config) -> None:
    """Render a prominent country banner at the top of the page (visible in demo video)."""
    flag = _FLAG_BY_CC.get(config.country_code, "🌍")
    st.markdown(
        f"""<div class="country-banner">
            <span class="country-banner-flag">{flag}</span>
            <div class="country-banner-meta">
                <div class="country-banner-name">{config.country}</div>
                <div class="country-banner-sub">
                    {config.labor_data.currency} ·
                    {config.ui.primary_language.upper()} ·
                    LMIC factor {config.automation_calibration.lmic_adjustment_factor}
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _apply_persona(p: dict) -> None:
    """on_click callback: stage the persona via non-widget keys.

    Streamlit 1.56 forbids writing to a widget-bound session_state key
    (country_select) even from a callback. We stage the desired country in
    `_pending_country`, which app.py copies into `country_select` BEFORE the
    selectbox is instantiated on the next rerun.
    """
    st.session_state["_pending_country"] = p["country"]
    st.session_state["form_description"] = p["text"]
    st.session_state["form_name"] = p["name"]
    st.session_state["form_education"] = p["education"]
    st.session_state["form_languages"] = p["languages"]
    for key in ("profile", "risk", "adjacent", "matches",
                "wage_signal", "growth_signal", "dashboard"):
        st.session_state.pop(key, None)


def _render_persona_buttons(config) -> None:
    """4 one-click demo personas. Switches country + prefills the form."""
    st.markdown(f"#### {t('youth.persona_section_title')}")
    st.caption(t("youth.persona_section_caption"))
    cols = st.columns(len(_PERSONAS))
    for col, p in zip(cols, _PERSONAS):
        with col:
            label = f"{p['flag']} {p['name']}, {p['age']}"
            help_text = (
                f"{p['city']} ({p['country']}) — {p['tagline']}. "
                f"Click to load this persona and switch to {p['country']}."
            )
            is_active = (config.country_code == p["country"])
            btn_type = "primary" if is_active else "secondary"
            st.button(
                label,
                key=f"persona_{p['country']}",
                use_container_width=True,
                help=help_text,
                type=btn_type,
                on_click=_apply_persona,
                args=(p,),
            )
            st.caption(p["tagline"])


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
        st.error(t("error.api_unreachable", url=API_BASE))
        return

    # ── Active country banner (B) ─────────────────────────────────
    _render_country_banner(config)

    # ── Demo personas (A) — quick one-click prefill, separate from form ──
    _render_persona_buttons(config)

    # ── Header ────────────────────────────────────────────────────
    st.markdown(f"### {t('youth.form_section_title')}")
    st.caption(t("youth.form_section_caption"))

    # ── Form initial values (driven by session_state for persona prefill) ──
    edu_levels = config.education_taxonomy.levels
    default_edu = st.session_state.get("form_education")
    if default_edu not in edu_levels:
        # Country switched + persona's education level not in this country's ladder.
        default_edu = edu_levels[min(2, len(edu_levels) - 1)]
    default_text = st.session_state.get("form_description", _DEMO_TEXT)
    default_name = st.session_state.get("form_name", "Akossiwa")
    default_langs = [
        l for l in st.session_state.get("form_languages", [config.ui.primary_language])
        if l in config.ui.supported_languages
    ] or [config.ui.primary_language]

    # ── Input form ────────────────────────────────────────────────
    with st.form("profile_form", clear_on_submit=False):
        description = st.text_area(
            t("youth.form.text_label"),
            value=default_text,
            height=140,
            placeholder=t("youth.form.text_placeholder"),
            help=t("youth.form.text_help"),
        )
        c1, c2 = st.columns(2)
        with c1:
            edu = st.selectbox(
                t("youth.form.education"),
                edu_levels,
                index=edu_levels.index(default_edu),
            )
        with c2:
            langs = st.multiselect(
                t("youth.form.languages"),
                config.ui.supported_languages,
                default=default_langs,
            )
        name = st.text_input(t("youth.form.name"), value=default_name)
        submitted = st.form_submit_button(
            t("youth.form.submit"), use_container_width=True
        )

    if submitted:
        if not description.strip():
            st.error(t("youth.form.empty_error"))
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

        tab1, tab2, tab3, tab4 = st.tabs([
            t("tabs.profile"),
            t("tabs.risk"),
            t("tabs.opportunities"),
            t("tabs.mirror"),
        ])
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
            f"{t('footer.tagline', country=config.country)}"
            "</p>",
            unsafe_allow_html=True,
        )
