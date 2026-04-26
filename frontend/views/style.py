"""Custom CSS injection for UNMAPPED frontend."""

import streamlit as st

_CSS = """
<style>
/* ── Import font ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Apply Inter to body only — Streamlit's icon glyphs (Material Icons /
 * Material Symbols) live inside st-* classes and MUST keep their own font,
 * otherwise the icon name renders as literal text ("keyboard_arrow_right"). */
html, body, .stApp, .stMarkdown, .stCaption {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* Defensive: never touch icon-font elements */
.material-icons,
.material-icons-outlined,
[class*="material-symbols"],
[class*="MuiSvgIcon"],
[data-testid*="icon"] {
    font-family: revert !important;
}

/* ── Hide Streamlit chrome ───────────────────────────────── */
/* NB: do NOT hide `header` — it contains the sidebar collapse/expand
   button. Hide the menu, footer, and deploy button only. */
#MainMenu, footer, .stDeployButton { visibility: hidden; height: 0; }

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

/* ── Gap cards (side-by-side realistic vs aspirational) ─────────────────── */
.gap-card {
    background: linear-gradient(135deg, #1A1D23, #0E1117);
    border: 1px solid #2A2D35;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    height: 100%;
}
.gap-card.realistic { border-color: #00D4AA55; }
.gap-card.aspirational { border-color: #0066FF55; }
.gap-label {
    font-size: 0.72rem;
    color: #B8BCC8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.3rem;
}
.gap-value {
    font-size: 1.55rem;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.1;
}
.gap-card.realistic .gap-value { color: #00D4AA; }
.gap-card.aspirational .gap-value { color: #6BA8FF; }
.gap-meta {
    font-size: 0.78rem;
    color: #B8BCC8;
    margin-top: 0.35rem;
}

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
/* Primary = the action button (green gradient) */
.stButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #00D4AA, #00A88A) !important;
    color: #0E1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    width: 100%;
}
/* Secondary = inactive persona, less prominent */
.stButton > button[kind="secondary"] {
    background: #1A1D23 !important;
    color: #B8BCC8 !important;
    border: 1px solid #2A2D35 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 0.55rem 1.4rem !important;
    width: 100%;
}
/* Default Streamlit button (no kind specified) */
.stButton > button:not([kind]) {
    background: linear-gradient(135deg, #00D4AA, #00A88A) !important;
    color: #0E1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    width: 100%;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stButton > button[kind="secondary"]:hover {
    border-color: #00D4AA66 !important;
    color: #00D4AA !important;
}
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

/* ── Profile tab — summary banner ─────────────────────────── */
.profile-summary-banner {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: #1A1D23;
    border: 1px solid #2A2D35;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin: 0.5rem 0 1rem 0;
    flex-wrap: wrap;
}
.profile-summary-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
}
.profile-summary-num {
    font-size: 1.6rem;
    font-weight: 700;
    color: #00D4AA;
    line-height: 1;
}
.profile-summary-label {
    font-size: 0.7rem;
    color: #B8BCC8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.2rem;
    text-align: center;
}
.profile-summary-divider {
    color: #2A2D35;
    font-size: 1.5rem;
}
.profile-summary-meta {
    flex: 1;
    font-size: 0.78rem;
    color: #B8BCC8;
}
.profile-summary-meta code {
    background: transparent !important;
    color: #00D4AA;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.78rem;
    padding: 0 !important;
}

/* ── Profile tab — category cards (the human-readable view) ─── */
.category-card {
    background: #1A1D23;
    border: 1px solid #2A2D35;
    border-left: 4px solid #2A2D35;  /* overridden inline by category color */
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
}
.cat-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.7rem;
}
.cat-dot {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    flex-shrink: 0;
}
.cat-name {
    font-size: 0.85rem;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.04em;
}
.cat-count {
    margin-left: auto;
    font-size: 0.72rem;
    color: #B8BCC8;
    background: #0E1117;
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #2A2D35;
}
.cat-skills { display: flex; flex-direction: column; gap: 0.5rem; }
.cat-skill {
    background: #0E1117;
    border: 1px solid #2A2D35;
    border-radius: 6px;
    padding: 0.5rem 0.7rem;
}
.cat-skill-label {
    color: #FFFFFF;
    font-size: 0.92rem;
    font-weight: 500;
}
.cat-skill-meta {
    color: #B8BCC8;
    font-size: 0.74rem;
    margin-top: 0.2rem;
}
.cat-adj-section {
    margin-top: 0.8rem;
    padding-top: 0.7rem;
    border-top: 1px dashed #2A2D35;
}
.cat-adj-title {
    font-size: 0.75rem;
    color: #00D4AA;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.cat-adj-list {
    margin: 0;
    padding-left: 1.1rem;
    list-style: none;
}
.cat-adj-list li {
    color: #FFFFFF;
    font-size: 0.84rem;
    margin-bottom: 0.25rem;
    position: relative;
}
.cat-adj-list li::before {
    content: "•";
    color: #00D4AA;
    position: absolute;
    left: -1rem;
}
.cat-adj-meta {
    color: #6B7280;
    font-size: 0.72rem;
}

/* ── Recommended next steps callout (Mirror tab hero CTA) ──── */
.next-steps-callout {
    background: linear-gradient(135deg, #00D4AA12, #00D4AA05);
    border: 1px solid #00D4AA66;
    border-left: 4px solid #00D4AA;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin: 1rem 0 1.4rem 0;
}
.next-steps-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #00D4AA;
    letter-spacing: 0.02em;
    margin-bottom: 0.7rem;
    text-transform: uppercase;
}
.next-step-item {
    display: flex;
    gap: 0.7rem;
    align-items: flex-start;
    margin-bottom: 0.6rem;
    line-height: 1.5;
}
.next-step-item:last-child { margin-bottom: 0; }
.next-step-num {
    flex-shrink: 0;
    width: 1.6rem; height: 1.6rem;
    border-radius: 50%;
    background: #00D4AA;
    color: #0E1117;
    font-weight: 700;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
.next-step-text {
    color: #FFFFFF;
    font-size: 0.88rem;
}

/* ── Country banner (top of page, visible in demo video) ───── */
.country-banner {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: linear-gradient(135deg, #1A1D23, #0E1117);
    border: 1px solid #00D4AA44;
    border-left: 4px solid #00D4AA;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin: 0 0 1.2rem 0;
}
.country-banner-flag { font-size: 2.2rem; line-height: 1; }
.country-banner-meta { display: flex; flex-direction: column; gap: 0.15rem; }
.country-banner-name {
    font-size: 1.25rem; font-weight: 700; color: #FFFFFF; line-height: 1;
}
.country-banner-sub {
    font-size: 0.78rem; color: #B8BCC8; letter-spacing: 0.02em;
}

/* ── Demo persona button captions ─────────────────────────── */
.stCaption {
    font-size: 0.72rem !important;
}

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
