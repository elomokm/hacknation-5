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

from views.i18n import SUPPORTED as SUPPORTED_LANGS, t
from views.policymaker_view import render_policymaker_view
from views.style import inject_custom_css
from views.youth_view import render_youth_view

inject_custom_css()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"## {t('sidebar.title')}",
        help="Closing the distance between informal skills and economic opportunity",
    )
    st.caption(t("sidebar.subtitle"))

    st.divider()

    # UI language toggle — drives all chrome strings via t()
    ui_lang = st.radio(
        t("sidebar.language"),
        options=SUPPORTED_LANGS,
        format_func=lambda x: {"en": "🇬🇧 English", "fr": "🇫🇷 Français"}[x],
        horizontal=True,
        key="ui_lang",
    )

    st.divider()

    # Country toggle — auto-discovered from configs/, sorted alphabetically
    country = st.selectbox(
        t("sidebar.country"),
        options=["BEN", "GHA", "SEN", "BGD"],
        format_func=lambda x: {
            "BEN": "🇧🇯 Bénin",
            "SEN": "🇸🇳 Sénégal",
            "GHA": "🇬🇭 Ghana",
            "BGD": "🇧🇩 Bangladesh",
        }[x],
        key="country_select",
    )
    # Update env var so get_active_config() picks it up
    os.environ["ACTIVE_COUNTRY"] = country

    st.divider()

    # View selector
    view = st.radio(
        t("sidebar.interface"),
        options=["youth", "policymaker"],
        format_func=lambda x: {
            "youth": t("sidebar.youth"),
            "policymaker": t("sidebar.policymaker"),
        }[x],
    )

    st.divider()

    with st.expander(t("sidebar.about")):
        st.markdown(t("sidebar.about_body"))

# ── Main content ───────────────────────────────────────────────────────────
if view == "youth":
    render_youth_view()
else:
    render_policymaker_view()
