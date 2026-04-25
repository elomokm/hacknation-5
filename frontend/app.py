"""UNMAPPED — Streamlit entry point. Implemented in Phase 3."""

import logging
import os

import requests
import streamlit as st

from views.youth_view import render_youth_view
from views.policymaker_view import render_policymaker_view

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="UNMAPPED",
    page_icon="🗺️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -- Sidebar: view toggle + health check --
with st.sidebar:
    st.title("UNMAPPED")
    view = st.radio("View", ["Youth", "Policymaker"], index=0)
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        info = r.json()
        st.success(f"Backend OK · {info.get('country', '?')}")
    except Exception:
        st.error("Backend offline — run `make backend`")

if view == "Youth":
    render_youth_view(backend_url=BACKEND_URL)
else:
    render_policymaker_view(backend_url=BACKEND_URL)
