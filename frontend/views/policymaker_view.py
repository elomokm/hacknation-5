"""Policymaker-facing view — aggregate signals + data sources. Implemented in Phase 3."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def render_policymaker_view(backend_url: str) -> None:
    """Render the policymaker dashboard with aggregate signals and honest limits."""
    st.title("Tableau de bord — Décideurs")

    st.info("Données agrégées disponibles en Phase 3.")

    with st.expander("Limites & transparence des données"):
        st.markdown("""
        **Ce que UNMAPPED ne fait pas :**
        - Il ne prédit pas l'employabilité individuelle
        - Les scores d'automatisation sont basés sur Frey-Osborne (2013), calibrés LMIC
        - Les données ILOSTAT peuvent avoir 1–2 ans de décalage
        - Les correspondances ESCO sont probabilistes, pas certaines

        **Sources :**
        - ILOSTAT — salaires et emploi par secteur
        - Frey & Osborne (2017) — probabilités d'automatisation
        - ESCO v1.2 — taxonomie des compétences
        - Wittgenstein Centre — projections éducatives
        """)
