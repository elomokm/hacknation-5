"""UNMAPPED — Streamlit frontend entry point."""

import os
import sys
from pathlib import Path

import requests
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
from views.operator_view import render_operator_view
from views.policymaker_view import render_policymaker_view
from views.style import inject_custom_css
from views.youth_view import render_youth_view

inject_custom_css()


# ── Country list — dynamic from API so newly-onboarded countries appear ──
def _resolve_api_url() -> str:
    if os.getenv("UNMAPPED_API_URL"):
        return os.environ["UNMAPPED_API_URL"]
    try:
        if "UNMAPPED_API_URL" in st.secrets:
            return st.secrets["UNMAPPED_API_URL"]
    except Exception:
        pass
    return "http://localhost:8000/api"


# Display labels for known countries — falls back to "🌍 {api name}" otherwise.
# The fallback is intentional: a freshly-onboarded country shows up immediately
# even without a hardcoded entry here.
_KNOWN_LABELS: dict[str, str] = {
    "BEN": "🇧🇯 Bénin",
    "SEN": "🇸🇳 Sénégal",
    "GHA": "🇬🇭 Ghana",
    "BGD": "🇧🇩 Bangladesh",
}


@st.cache_data(ttl=10, show_spinner=False)
def _fetch_countries(api_base: str) -> list[dict]:
    """Hit /api/config/countries. TTL=10s so live onboards show up fast."""
    try:
        r = requests.get(f"{api_base}/config/countries", timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    # Fallback: hardcoded list keeps the UI alive when the API is cold/down.
    return [{"code": c, "name": _KNOWN_LABELS[c].split(" ", 1)[1]} for c in _KNOWN_LABELS]


def _country_label(code: str, name: str) -> str:
    return _KNOWN_LABELS.get(code, f"🌍 {name}")


api_base = _resolve_api_url()
countries = _fetch_countries(api_base)
country_options = sorted([c["code"] for c in countries])
code_to_name = {c["code"]: c.get("name", c["code"]) for c in countries}

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

    # Apply pending country switch (from persona buttons) BEFORE the widget is
    # instantiated. Streamlit 1.56 forbids writing to a widget-bound key after
    # the widget renders, even from a callback.
    if "_pending_country" in st.session_state:
        pending = st.session_state.pop("_pending_country")
        if pending in country_options:
            st.session_state["country_select"] = pending

    # Country toggle — populated from /api/config/countries, so live-onboarded
    # countries appear here within ~10s without a frontend redeploy.
    country = st.selectbox(
        t("sidebar.country"),
        options=country_options,
        format_func=lambda code: _country_label(code, code_to_name.get(code, code)),
        key="country_select",
    )
    # Update env var so get_active_config() picks it up
    os.environ["ACTIVE_COUNTRY"] = country

    st.divider()

    # View selector — Youth / Policymaker / Operator
    view = st.radio(
        t("sidebar.interface"),
        options=["youth", "policymaker", "operator"],
        format_func=lambda x: {
            "youth": t("sidebar.youth"),
            "policymaker": t("sidebar.policymaker"),
            "operator": t("sidebar.operator"),
        }[x],
    )

    st.divider()

    with st.expander(t("sidebar.about")):
        st.markdown(t("sidebar.about_body"))

# ── Main content ───────────────────────────────────────────────────────────
if view == "youth":
    render_youth_view()
elif view == "policymaker":
    render_policymaker_view()
else:
    render_operator_view()
