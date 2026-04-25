"""Module 02 — Adjacent skill finder: NetworkX graph over ESCO skills.

No LLM calls. Pure graph algorithm.
Edge weight = same_category(0.5) + shared_isco(0.3/group) + jaccard(0.2).
Threshold: 0.35 to create an edge.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import networkx as nx

from core.models import (
    AdjacentSkill,
    CountryConfig,
    MappedSkill,
    Skill,
    SkillRiskScore,
)
from module_02_risk.automation_scorer import AutomationScorer

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_EDGE_THRESHOLD = 0.35

_STOP: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "to", "for", "with",
    "by", "on", "at", "is", "are", "be", "its", "this", "that",
    "basic", "general", "advanced", "junior", "senior",
})


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, remove stop words, 5-char stem."""
    tokens = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    stemmed = set()
    for t in tokens:
        if t not in _STOP and len(t) > 2:
            stemmed.add(t[:5] if len(t) > 5 else t)
    return stemmed


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class AdjacentSkillsFinder:
    """NetworkX-based skill adjacency for upskilling pathway discovery."""

    def __init__(self) -> None:
        """Load ESCO skills and build the weighted adjacency graph."""
        self._skills: list[Skill] = self._load_skills()
        self._skill_index: dict[str, Skill] = {s.esco_id: s for s in self._skills}
        self._tokens: dict[str, set[str]] = {
            s.esco_id: _tokenize(s.label) for s in self._skills
        }
        self._graph = self._build_graph()
        logger.info(
            "AdjacentSkillsFinder ready: %d nodes, %d edges",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_durable_alternatives(
        self,
        current_skill: MappedSkill,
        risk_score: SkillRiskScore,
        scorer: AutomationScorer,
        config: CountryConfig,
        top_k: int = 3,
    ) -> list[AdjacentSkill]:
        """Return top-k lower-risk ESCO skills adjacent to current_skill.

        Filters to risk_band in ["low", "moderate"], sorts by risk asc then weight desc.
        Returns empty list if current skill is not in the graph or has no durable neighbors.
        """
        if current_skill.esco_id not in self._graph:
            logger.debug("Skill %s not in graph", current_skill.esco_id)
            return []

        lmic_factor = config.automation_calibration.lmic_adjustment_factor
        neighbors = self._graph[current_skill.esco_id]
        alternatives: list[AdjacentSkill] = []

        for neighbor_id, edge_data in neighbors.items():
            neighbor = self._skill_index.get(neighbor_id)
            if neighbor is None:
                continue

            neighbor_risk = scorer.score_skill(
                esco_id=neighbor.esco_id,
                esco_label=neighbor.label,
                isco_groups=neighbor.isco_groups,
                lmic_factor=lmic_factor,
            )

            if neighbor_risk.risk_band not in {"low", "moderate"}:
                continue

            rationale = self._build_rationale(
                current_skill=current_skill,
                neighbor=neighbor,
                neighbor_risk=neighbor_risk,
                current_risk=risk_score,
                edge_weight=edge_data["weight"],
            )

            alternatives.append(AdjacentSkill(
                esco_id=neighbor.esco_id,
                esco_label=neighbor.label,
                esco_category=neighbor.category,
                automation_risk=neighbor_risk,
                proximity_score=round(edge_data["weight"], 3),
                transition_rationale=rationale,
            ))

        # Sort: lowest risk first, then highest proximity
        alternatives.sort(
            key=lambda x: (
                x.automation_risk.adjusted_probability or 1.0,
                -x.proximity_score,
            )
        )
        return alternatives[:top_k]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_skills(self) -> list[Skill]:
        """Load ESCO skills subset from JSON."""
        path = _DATA_DIR / "esco" / "skills_subset.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Skill(**s) for s in raw]

    def _build_graph(self) -> nx.Graph:
        """Build weighted skill adjacency graph."""
        G: nx.Graph = nx.Graph()
        for skill in self._skills:
            G.add_node(skill.esco_id, skill=skill)

        skills = self._skills
        n = len(skills)
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = skills[i], skills[j]
                weight = self._edge_weight(s1, s2)
                if weight >= _EDGE_THRESHOLD:
                    G.add_edge(s1.esco_id, s2.esco_id, weight=round(weight, 3))

        return G

    def _edge_weight(self, s1: Skill, s2: Skill) -> float:
        """Compute edge weight between two ESCO skills."""
        cat_score = 0.5 if s1.category == s2.category else 0.0

        shared_isco = len(set(s1.isco_groups) & set(s2.isco_groups))
        isco_score = min(shared_isco * 0.3, 0.6)  # cap at 0.6

        j = _jaccard(self._tokens[s1.esco_id], self._tokens[s2.esco_id])
        jaccard_score = j * 0.2

        return min(1.0, cat_score + isco_score + jaccard_score)

    def _build_rationale(
        self,
        current_skill: MappedSkill,
        neighbor: Skill,
        neighbor_risk: SkillRiskScore,
        current_risk: SkillRiskScore,
        edge_weight: float,
    ) -> str:
        """Generate a 1-sentence algorithmic transition rationale."""
        shared_isco = sorted(
            set(current_skill.isco_groups) & set(neighbor.isco_groups)
        )

        adj_prob = (
            f"{neighbor_risk.adjusted_probability:.2f}"
            if neighbor_risk.adjusted_probability is not None
            else "unknown"
        )
        cur_prob = (
            f"{current_risk.adjusted_probability:.2f}"
            if current_risk.adjusted_probability is not None
            else "unknown"
        )

        if shared_isco:
            code = shared_isco[0]
            return (
                f"Shares ISCO group {code} with {current_skill.esco_label} — "
                f"{neighbor.label} carries lower adjusted automation risk "
                f"({adj_prob} vs {cur_prob} for your current skill)."
            )
        elif current_skill.esco_category == neighbor.category:
            return (
                f"Both fall under {neighbor.category} — {neighbor.label} "
                f"shows lower displacement risk ({adj_prob} adjusted) "
                f"than {current_skill.esco_label} ({cur_prob})."
            )
        else:
            return (
                f"{neighbor.label} is closely connected to your skills "
                f"(proximity {edge_weight:.2f}) and carries lower automation "
                f"risk ({adj_prob} adjusted)."
            )
