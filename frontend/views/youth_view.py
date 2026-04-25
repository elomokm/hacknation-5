"""Youth-facing view — skill input + opportunity results. Implemented in Phase 3."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def render_youth_view(backend_url: str) -> None:
    """Render the youth-facing skill input and opportunity results panel."""
    st.title("Décris ton travail")
    st.caption("En quelques phrases, dis-nous ce que tu sais faire.")

    description = st.text_area(
        label="Ton expérience",
        placeholder="Ex: Je répare des téléphones depuis 3 ans. Je gère les pièces sur WhatsApp...",
        height=120,
    )

    if st.button("Analyser →", type="primary"):
        if not description.strip():
            st.warning("Décris au moins une compétence.")
            return
        with st.spinner("Analyse en cours..."):
            st.info("Pipeline complet disponible en Phase 3.")
