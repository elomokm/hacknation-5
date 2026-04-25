"""Custom CSS injection for UNMAPPED frontend."""

import streamlit as st

_CSS = """
<style>
/* ── Import font ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* ── Hide Streamlit chrome ───────────────────────────────── */
#MainMenu, footer, header, .stDeployButton { visibility: hidden; height: 0; }

/* ── Main container — mobile-first ──────────────────────── */
.main .block-container {
    max-width: 740px;
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    margin: 0 auto;
}

/* ── Typography ──────────────────────────────────────────── */
h1 { font-weight: 700; letter-spacing: -0.03em; line-height: 1.2; }
h2 { font-weight: 700; letter-spacing: -0.02em; }
h3 { font-weight: 600; }
p  { line-height: 1.6; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0D1016 !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label { color: #B8BCC8; }

/* ── Metric cards ────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1A1D23;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    border: 1px solid #2A2D35;
}
[data-testid="stMetricLabel"] { color: #B8BCC8 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 700; font-size: 1.4rem !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Wage mirror hero ────────────────────────────────────── */
.wage-mirror-hero {
    background: linear-gradient(135deg, #00D4AA18, #0066FF10);
    border: 1px solid #00D4AA44;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
}
.wage-label {
    font-size: 0.72rem;
    color: #B8BCC8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.2rem;
}
.wage-value-primary { font-size: 1.9rem; font-weight: 700; color: #00D4AA; line-height: 1.1; }
.wage-value-secondary { font-size: 1.6rem; font-weight: 700; color: #FFFFFF; line-height: 1.1; }
.wage-delta-up   { font-size: 0.82rem; color: #00D4AA; font-weight: 600; }
.wage-delta-down { font-size: 0.82rem; color: #FF6B6B; font-weight: 600; }
.data-note { font-size: 0.72rem; color: #6B7280; font-style: italic; margin-top: 0.5rem; }

/* ── Risk band badges ────────────────────────────────────── */
.risk-low      { background:#00D4AA18; color:#00D4AA; border:1px solid #00D4AA44; border-radius:5px; padding:2px 8px; font-size:0.76rem; font-weight:600; }
.risk-moderate { background:#FFA94D18; color:#FFA94D; border:1px solid #FFA94D44; border-radius:5px; padding:2px 8px; font-size:0.76rem; font-weight:600; }
.risk-high     { background:#FF6B6B18; color:#FF6B6B; border:1px solid #FF6B6B44; border-radius:5px; padding:2px 8px; font-size:0.76rem; font-weight:600; }
.risk-critical { background:#FF3B3B22; color:#FF3B3B; border:1px solid #FF3B3B66; border-radius:5px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.risk-no_match { background:#2A2D3518; color:#6B7280; border:1px solid #2A2D35; border-radius:5px; padding:2px 8px; font-size:0.76rem; }

/* ── Skill chip ──────────────────────────────────────────── */
.skill-chip {
    display: inline-block;
    background: #1A1D23;
    border: 1px solid #2A2D35;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.78rem;
    color: #B8BCC8;
    margin: 2px;
}

/* ── Opportunity cards ───────────────────────────────────── */
.opp-card {
    background: #1A1D23;
    border: 1px solid #2A2D35;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.opp-card:hover { border-color: #00D4AA33; }
.opp-title { font-weight: 600; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.15rem; }
.opp-meta  { font-size: 0.78rem; color: #B8BCC8; }
.opp-score-bar { height: 4px; border-radius: 2px; background: linear-gradient(90deg, #00D4AA, #0066FF); margin-top: 0.5rem; }

/* ── Tabs ────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #1A1D23;
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    color: #B8BCC8;
    font-weight: 500;
    font-size: 0.85rem;
    padding: 0.4rem 0.8rem;
}
.stTabs [aria-selected="true"] {
    background: #00D4AA22 !important;
    color: #00D4AA !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {
    background: linear-gradient(135deg, #00D4AA, #00A88A) !important;
    color: #0E1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    width: 100%;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stDownloadButton > button {
    background: #1A1D23 !important;
    color: #00D4AA !important;
    border: 1px solid #00D4AA44 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* ── Progress bar ────────────────────────────────────────── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #00D4AA, #0066FF);
}

/* ── Info / warning boxes ────────────────────────────────── */
.stInfo  { background: #00D4AA10; border-color: #00D4AA44; }
.stAlert { border-radius: 8px; }

/* ── Expander ────────────────────────────────────────────── */
.streamlit-expanderHeader { font-size: 0.82rem; color: #B8BCC8 !important; }

/* ── Divider ─────────────────────────────────────────────── */
hr { border-color: #2A2D35; }

/* ── Mobile ──────────────────────────────────────────────── */
@media (max-width: 480px) {
    .main .block-container { padding-left: 0.5rem; padding-right: 0.5rem; }
    h1 { font-size: 1.35rem; }
    .wage-value-primary  { font-size: 1.4rem; }
    .wage-value-secondary { font-size: 1.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
}
</style>
"""


def inject_custom_css() -> None:
    """Inject UNMAPPED custom CSS into the Streamlit app."""
    st.markdown(_CSS, unsafe_allow_html=True)


def risk_badge(band: str) -> str:
    """Return HTML badge for a risk band."""
    labels = {
        "low": "Low",
        "moderate": "Moderate",
        "high": "High",
        "critical": "Critical",
        "no_match": "No data",
    }
    return f'<span class="risk-{band}">{labels.get(band, band)}</span>'
