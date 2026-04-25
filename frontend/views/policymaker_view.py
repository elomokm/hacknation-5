"""Policymaker-facing aggregate dashboard."""

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.config_loader import get_active_config
from module_03_opportunity.econometrics import EconometricSignals


@st.cache_resource
def _get_econ(country_code: str):
    from core.config_loader import load_config
    return EconometricSignals(load_config(country_code))


def render_policymaker_view() -> None:
    """Render the policymaker aggregate signals dashboard."""
    config = get_active_config()
    econ = _get_econ(config.country_code)
    labor = econ._labor

    # ── Header ──────────────────────────────────────────────────
    st.markdown(f"## {config.country} — Youth Skills Dashboard")
    st.caption(f"Aggregate labor market signals · {labor.year} reference · ILOSTAT")

    st.divider()

    # ── Key metrics row ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Youth unemployment", f"{labor.youth_unemployment_rate:.1f}%")
    with c2:
        neet = getattr(labor, "youth_neet_rate", None)
        st.metric("Youth NEET", f"{neet:.1f}%" if neet else "n/a")
    with c3:
        st.metric("Informal employment", f"{labor.informal_employment_share:.1f}%")
    with c4:
        pop = getattr(labor, "population_15_24", None)
        st.metric("Population 15-24", f"{pop/1_000_000:.1f}M" if pop else "n/a")

    st.divider()

    # ── Signal 1 — Wage by sector ────────────────────────────────
    st.markdown("### 💰 Wage Signal — Monthly median by sector")
    st.caption("ILOSTAT 2024 · XOF (CFA Franc)")

    wages = sorted(labor.wage_by_sector, key=lambda w: w.median_monthly_xof)
    fig_wage = go.Figure(go.Bar(
        x=[w.median_monthly_xof for w in wages],
        y=[w.sector[:35] for w in wages],
        orientation="h",
        marker=dict(
            color=[w.median_monthly_xof for w in wages],
            colorscale=[[0, "#1A1D23"], [0.4, "#2A5298"], [1.0, "#00D4AA"]],
            showscale=False,
        ),
        text=[f"{w.median_monthly_xof:,} XOF" for w in wages],
        textposition="outside",
        textfont=dict(size=10, color="#B8BCC8"),
    ))
    fig_wage.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="#B8BCC8", size=11)),
        margin=dict(l=0, r=80, t=10, b=10),
        height=max(280, len(wages) * 28),
    )
    st.plotly_chart(fig_wage, use_container_width=True)

    st.markdown(
        '<p class="data-note">Source: ILOSTAT · Wages are sector medians — '
        "individual earnings vary significantly. ICT/Finance wages reflect "
        "urban formal sector; agriculture is largely informal subsistence.</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Signal 2 — Employment share ──────────────────────────────
    st.markdown("### 👷 Employment Signal — Sector share")
    st.caption("ILOSTAT 2024 · % of total employment")

    growth = econ.get_growth_signals()
    emp_sorted = sorted(growth.sectors, key=lambda s: s["employment_share_pct"], reverse=True)

    fig_emp = go.Figure(go.Bar(
        x=[s["employment_share_pct"] for s in emp_sorted],
        y=[s["sector"][:35] for s in emp_sorted],
        orientation="h",
        marker_color=[
            "#00D4AA" if s["sector"] in growth.growth_flagged_sectors else "#2A5298"
            for s in emp_sorted
        ],
        text=[f"{s['employment_share_pct']:.1f}%" for s in emp_sorted],
        textposition="outside",
        textfont=dict(size=10, color="#B8BCC8"),
    ))
    fig_emp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="#B8BCC8", size=11)),
        margin=dict(l=0, r=60, t=10, b=10),
        height=max(280, len(emp_sorted) * 28),
    )
    st.plotly_chart(fig_emp, use_container_width=True)

    if growth.growth_flagged_sectors:
        st.info(
            f"**High-value sectors** (highlighted in green): "
            + ", ".join(growth.growth_flagged_sectors)
            + " — wage premium significantly above national median."
        )

    st.markdown(
        '<p class="data-note">' + growth.methodology_note + "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Recommended program areas ────────────────────────────────
    st.markdown("### 🎯 Recommended Program Areas")
    st.caption("Data-driven — derived from wage gap and sector signals")

    usd = config.labor_data.usd_conversion_rate
    ict_xof = next(
        (w.median_monthly_xof for w in labor.wage_by_sector if "ICT" in w.sector), None
    )
    informal_xof = next(
        (w.median_monthly_xof for w in labor.wage_by_sector if "informal" in w.sector.lower()), 35000
    )
    agri_pct = next(
        (e.share_pct for e in labor.employment_by_sector if "Agriculture" in e.sector), 0
    )

    programs = [
        (
            "Digital skills — highest wage-per-worker sector",
            f"ICT median: {ict_xof:,} XOF/month vs informal trade {informal_xof:,} XOF "
            f"(×{ict_xof // max(informal_xof, 1):.1f} gap). "
            "Target: ISCO 25/35 certifications.",
        ),
        (
            "TVET electronics/maintenance",
            "ISCO 74 (Electrical & Electronic Trades) — accessible with BEPC, "
            "aligns with mobile repair informal skills. GIZ and national TVET programs.",
        ),
        (
            "Agricultural value-chain formalization",
            f"{agri_pct:.0f}% of workforce in agriculture. "
            "Agro-processing and cooperative management uplift from subsistence to market-oriented.",
        ),
        (
            "Financial literacy and mobile money",
            "Mobile money penetration high. Bridging informal financial skills to "
            "formal microfinance and banking (ISCO 33/24).",
        ),
    ]

    for title, detail in programs:
        with st.expander(f"📌 {title}"):
            st.write(detail)

    st.divider()

    # ── Methodology and limits ───────────────────────────────────
    with st.expander("⚠️ Methodology & Limitations"):
        st.markdown(f"""
**Data sources:**
- **ILOSTAT** — {labor.country} labor force survey {labor.year}: wage by sector, employment share, unemployment
- **Frey-Osborne (2017)** — automation probabilities, LMIC-adjusted (factor {config.automation_calibration.lmic_adjustment_factor})
- **ESCO v1.2** — skill taxonomy (~150 skill subset)
- **Wittgenstein Centre SSP2** — West Africa education projections 2025–2035

**Known limitations:**
- Wage figures are sector medians — intra-sector dispersion is large
- No gender disaggregation available in this dataset
- ILOSTAT data may lag 1-2 years from current conditions
- Automation adjustment factor is pragmatic, not empirically validated for {labor.country}
- "Growth flagged" sectors are based on wage premium, not time-series growth rates
        """)
