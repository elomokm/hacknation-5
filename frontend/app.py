"""UNMAPPED — Streamlit frontend entry point."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load API key from backend/.env before any backend import
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Make backend importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import streamlit as st

# Page config must be first Streamlit call
st.set_page_config(
    page_title="UNMAPPED — Closing the distance",
    page_icon="🗺️",
    layout="centered",
    initial_sidebar_state="expanded",
)

from views.style import inject_custom_css
from views.youth_view import render_youth_view
from views.policymaker_view import render_policymaker_view

inject_custom_css()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "## UNMAPPED",
        help="Closing the distance between informal skills and economic opportunity",
    )
    st.caption("World Bank × Hack-Nation 5")

    st.divider()

    # Country toggle — the localizability proof
    country = st.selectbox(
        "Active country",
        options=["BEN", "SEN"],
        format_func=lambda x: {"BEN": "🇧🇯 Bénin", "SEN": "🇸🇳 Sénégal"}[x],
        key="country_select",
    )
    # Update env var so get_active_config() picks it up
    os.environ["ACTIVE_COUNTRY"] = country

    st.divider()

    # View selector
    view = st.radio(
        "Interface",
        options=["youth", "policymaker"],
        format_func=lambda x: {
            "youth": "Youth (Akossiwa)",
            "policymaker": "Policymaker",
        }[x],
    )

    st.divider()

    with st.expander("About"):
        st.markdown(
            """
**UNMAPPED** maps informal skills to economic opportunity
using real data — ESCO, ILOSTAT, Frey-Osborne.

- **Module 01** — Skill extraction & ESCO mapping
- **Module 02** — Automation risk (Frey-Osborne, LMIC-adjusted)
- **Module 03** — Opportunity matching + econometric signals

Challenge 5 · World Bank Youth Summit
Hack-Nation 5th Global AI Hackathon
            """
        )

# ── Main content ───────────────────────────────────────────────────────────
if view == "youth":
    render_youth_view()
else:
    render_policymaker_view()
