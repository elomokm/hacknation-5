"""Operator console — no-code country onboarding.

The persona this view is for: an NGO field officer or government program
manager. They do NOT write code. They have an ILOSTAT-aligned CSV (or have
filled the template we provide) and need their country live in UNMAPPED in
under a minute. This view is the proof that "infrastructure layer" is real,
not just a YAML I happened to write.
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

from views.i18n import t


# Reuse the API URL resolution logic shape used by youth_view.
def _resolve_api_url() -> str:
    if os.getenv("UNMAPPED_API_URL"):
        return os.environ["UNMAPPED_API_URL"]
    try:
        if "UNMAPPED_API_URL" in st.secrets:
            return st.secrets["UNMAPPED_API_URL"]
    except Exception:
        pass
    return "http://localhost:8000/api"


API_BASE = _resolve_api_url()


def _post_onboarding(
    csv_file: Any,
    payload: dict[str, str],
) -> tuple[int, dict | str]:
    """POST the multipart upload. Returns (status_code, body_or_text)."""
    files = {"csv": (csv_file.name, csv_file.getvalue(), "text/csv")}
    try:
        r = requests.post(
            f"{API_BASE}/onboarding/country",
            files=files,
            data=payload,
            timeout=60,
        )
    except requests.RequestException as e:
        return (-1, str(e))
    try:
        return (r.status_code, r.json())
    except ValueError:
        return (r.status_code, r.text)


def render_operator_view() -> None:
    """Render the operator console — single-tab onboarding flow."""
    st.markdown(f"### {t('operator.title')}")
    st.caption(t("operator.subtitle"))
    st.divider()

    # ── Step 1: Download template ───────────────────────────────────────
    st.markdown(f"#### {t('operator.step1_title')}")
    st.caption(t("operator.step1_caption"))

    template_url = f"{API_BASE}/onboarding/template.csv"
    st.markdown(
        f"<a href='{template_url}' target='_blank' "
        f"style='display:inline-block;padding:0.6em 1.2em;background:#22C55E;"
        f"color:white;border-radius:6px;text-decoration:none;font-weight:600;"
        f"margin:0.5em 0'>{t('operator.step1_button')}</a>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Step 2: Form ────────────────────────────────────────────────────
    st.markdown(f"#### {t('operator.step2_title')}")

    with st.form("onboard_country_form", clear_on_submit=False):
        csv_file = st.file_uploader(
            t("operator.field.csv"),
            type=["csv"],
            help="Drag & drop or click to upload",
        )

        c1, c2 = st.columns(2)
        with c1:
            country_name = st.text_input(
                t("operator.field.country_name"),
                placeholder="Côte d'Ivoire",
            )
            country_code = st.text_input(
                t("operator.field.country_code"),
                max_chars=3,
                placeholder="CIV",
            )
            currency = st.text_input(
                t("operator.field.currency"),
                max_chars=4,
                placeholder="XOF",
            )
        with c2:
            usd_rate = st.number_input(
                t("operator.field.usd_rate"),
                min_value=0.01,
                value=600.0,
                step=10.0,
                format="%.2f",
            )
            primary_language = st.text_input(
                t("operator.field.primary_language"),
                max_chars=3,
                placeholder="fr",
            )
            secondary_languages = st.text_input(
                t("operator.field.secondary_languages"),
                placeholder="en",
            )

        with st.expander(t("operator.advanced"), expanded=False):
            ac1, ac2 = st.columns(2)
            with ac1:
                youth_unemployment_rate = st.number_input(
                    t("operator.field.youth_unemployment_rate"),
                    min_value=0.0, max_value=100.0, value=12.0, step=0.5,
                )
                informal_employment_share = st.number_input(
                    t("operator.field.informal_employment_share"),
                    min_value=0.0, max_value=100.0, value=75.0, step=1.0,
                )
            with ac2:
                youth_neet_rate = st.number_input(
                    t("operator.field.youth_neet_rate"),
                    min_value=0.0, max_value=100.0, value=25.0, step=1.0,
                )
                lmic_adjustment_factor = st.slider(
                    t("operator.field.lmic_factor"),
                    min_value=0.10, max_value=1.0, value=0.65, step=0.05,
                )

        submitted = st.form_submit_button(
            t("operator.submit"),
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    # ── Submit handler ──────────────────────────────────────────────────
    if not csv_file:
        st.error(t("operator.csv_required"))
        return

    payload = {
        "country_name": country_name.strip(),
        "country_code": country_code.strip().upper(),
        "currency": currency.strip().upper(),
        "usd_rate": str(usd_rate),
        "primary_language": primary_language.strip().lower(),
        "secondary_languages": secondary_languages.strip(),
        "youth_unemployment_rate": str(youth_unemployment_rate),
        "informal_employment_share": str(informal_employment_share),
        "youth_neet_rate": str(youth_neet_rate),
        "lmic_adjustment_factor": str(lmic_adjustment_factor),
    }

    with st.spinner(t("operator.submitting")):
        status, body = _post_onboarding(csv_file, payload)

    if status == 200 and isinstance(body, dict):
        st.success(
            t(
                "operator.success_title",
                country_name=body["country_name"],
                country_code=body["country_code"],
            )
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Sectors imported", body["sectors_imported"])
        m2.metric("Total countries", len(body["available_countries"]))
        m3.metric("Was replacement", "Yes" if body["was_replacement"] else "No")
        st.write(
            f"**Growth strategic sectors detected:** "
            + ", ".join(body["growth_strategic_sectors"])
        )
        st.info(
            t(
                "operator.success_hint",
                country_code=body["country_code"],
            )
        )
        # Bust the dynamic country list cache so the sidebar picks up the new country.
        st.cache_data.clear()
        st.balloons()
    else:
        if isinstance(body, dict):
            err_text = body.get("detail", str(body))
        else:
            err_text = body
        st.error(f"Onboarding failed (status {status}): {err_text}")
