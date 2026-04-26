"""Obsidian-style skill graph rendering using PyVis.

Profile skills are centered (large, green accent). Adjacent ESCO skills
(top transferability neighbours from the AdjacentSkillsFinder graph) are
rendered around them with category-colour coding.

Pure rendering helper — fetches adjacency from /api/risk/assess response
or computes it locally if needed.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


_CATEGORY_COLOR: dict[str, str] = {
    "Mobile Repair":      "#FF6B6B",
    "Web Development":    "#5F95FF",
    "Digital Literacy":   "#7B9EFF",
    "Carpentry":          "#A0826D",
    "Welding":            "#D2691E",
    "Tailoring":          "#FF99CC",
    "Driving":            "#888888",
    "Hospitality":        "#FFA94D",
    "Agriculture":        "#7FBA00",
    "Healthcare Informal":"#3DC9B0",
    "Healthcare Formal":  "#00A88A",
    "Commerce":           "#FFB347",
    "IT Professional":    "#0066FF",
    "Management":         "#9B59B6",
    "Finance":            "#1ABC9C",
    "Marketing":          "#E67E22",
    "Education":          "#3498DB",
    "Engineering":        "#F39C12",
    "General Service":    "#95A5A6",
    "Social Work":        "#27AE60",
    "Agribusiness":       "#16A085",
}

_DEFAULT_COLOR = "#6B7280"
_PROFILE_NODE_COLOR = "#00D4AA"  # primary accent — profile skills


def render_skill_graph(profile, adjacent_skills: dict, max_neighbors: int = 2) -> Optional[str]:
    """Build an Obsidian-style force-directed graph and return raw HTML.

    Args:
        profile: StandardizedProfile (Pydantic) — has .skills (list[MappedSkill])
        adjacent_skills: dict {esco_id: list[AdjacentSkill]} from /risk/assess
        max_neighbors: number of adjacent neighbours per profile skill

    Returns the HTML string ready for st.components.v1.html(), or None
    if the profile has no mapped skills.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        logger.error("pyvis not installed — falling back to None")
        return None

    if not profile.skills:
        return None

    net = Network(
        height="480px",
        width="100%",
        bgcolor="#0E1117",
        font_color="#FFFFFF",
        notebook=False,
        directed=False,
        cdn_resources="in_line",
    )
    # Force-directed physics
    net.barnes_hut(
        gravity=-3000,
        central_gravity=0.15,
        spring_length=120,
        spring_strength=0.03,
        damping=0.4,
        overlap=0.1,
    )

    # ── Profile skill nodes (large, green) ───────────────────────
    profile_node_ids: set[str] = set()
    for skill in profile.skills:
        net.add_node(
            skill.esco_id,
            label=_short_label(skill.esco_label),
            title=f"{skill.esco_label}\n[{skill.esco_category}]\nISCO: {', '.join(skill.isco_groups)}",
            color={"background": _PROFILE_NODE_COLOR, "border": "#00A88A"},
            size=28,
            font={"size": 16, "color": "#0E1117", "face": "Inter"},
            borderWidth=3,
            shape="dot",
        )
        profile_node_ids.add(skill.esco_id)

    # ── Adjacent skill nodes (smaller, category color) ───────────
    seen_adjacents: set[str] = set()
    for skill in profile.skills:
        alts = adjacent_skills.get(skill.esco_id, [])[:max_neighbors]
        # If no precomputed adjacents (skill wasn't high-risk), still add
        # a couple "siblings" from the same category if available
        if not alts and skill.esco_id in adjacent_skills:
            continue

        for alt in alts:
            if alt.esco_id in profile_node_ids:
                continue  # already a profile node
            if alt.esco_id not in seen_adjacents:
                color = _CATEGORY_COLOR.get(alt.esco_category, _DEFAULT_COLOR)
                tooltip = (
                    f"{alt.esco_label}\n[{alt.esco_category}]\n"
                    f"Adjacent · risk {alt.automation_risk.risk_band}\n"
                    f"{alt.transition_rationale}"
                )
                net.add_node(
                    alt.esco_id,
                    label=_short_label(alt.esco_label),
                    title=tooltip,
                    color={"background": color, "border": color},
                    size=14,
                    font={"size": 11, "color": "#FFFFFF", "face": "Inter"},
                    borderWidth=1,
                    shape="dot",
                )
                seen_adjacents.add(alt.esco_id)

            net.add_edge(
                skill.esco_id,
                alt.esco_id,
                value=alt.proximity_score,
                color={"color": "#2A2D35", "opacity": 0.7},
                width=1 + alt.proximity_score * 2,
            )

    # ── Render to a temp HTML and return string ──────────────────
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        net.write_html(f.name, notebook=False, open_browser=False)
        html_path = Path(f.name)

    html = html_path.read_text(encoding="utf-8")
    try:
        html_path.unlink()
    except OSError:
        pass

    # PyVis adds a default white background — strip it via inline CSS override
    html = html.replace(
        "</head>",
        "<style>body{background:#0E1117!important;margin:0;padding:0;} "
        "#mynetwork{background:#0E1117!important;border:none!important;}</style></head>",
    )
    return html


def _short_label(label: str, max_len: int = 28) -> str:
    """Truncate long ESCO labels for graph node display."""
    if len(label) <= max_len:
        return label
    return label[: max_len - 1].rstrip() + "…"
