"""Builds and manages the Traji skill graph using NetworkX."""

import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_SEED_FILE = _DATA_DIR / "seed_skills.json"
_CACHE_FILE = _DATA_DIR / "graph_cache.pkl"

_STOP_WORDS = {
    "and", "or", "the", "a", "of", "for", "in", "to", "with",
    "basic", "general", "advanced", "simple", "small",
}

_CATEGORY_WEIGHTS = {
    ("Technical", "Digital"): 0.15,
    ("Digital", "Technical"): 0.15,
    ("Commercial", "Service"): 0.10,
    ("Service", "Commercial"): 0.10,
    ("Agricultural", "Commercial"): 0.08,
    ("Commercial", "Agricultural"): 0.08,
    ("Creative", "Service"): 0.08,
    ("Service", "Creative"): 0.08,
}

EDGE_THRESHOLD = 0.18


class SkillGraph:
    """Skill graph for Traji — nodes are skills, edges are transferability scores."""

    def __init__(self) -> None:
        """Initialise with empty graph and skill index."""
        self._graph: nx.Graph = nx.Graph()
        self._skills: list[dict] = []
        self._name_index: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_graph(self) -> nx.Graph:
        """Load skills and build the weighted skill graph.

        Returns cached graph if seed file hasn't changed.
        """
        if self._is_cache_valid():
            logger.info("Loading graph from cache")
            self._load_cache()
            return self._graph

        logger.info("Building graph from seed skills")
        t0 = time.time()

        self._skills = self._load_seeds()
        self._name_index = {s["name"].lower(): s for s in self._skills}

        self._graph = nx.Graph()
        for skill in self._skills:
            self._graph.add_node(
                skill["id"],
                name=skill["name"],
                category=skill["category"],
                formality_level=skill["formality_level"],
                region=skill["region"],
                economic_value=skill["economic_value"],
            )

        edge_count = 0
        for i, s1 in enumerate(self._skills):
            for s2 in self._skills[i + 1 :]:
                w = self._edge_weight(s1, s2)
                if w >= EDGE_THRESHOLD:
                    self._graph.add_edge(s1["id"], s2["id"], weight=w)
                    edge_count += 1

        elapsed = time.time() - t0
        logger.info(
            "Graph built in %.2fs — %d nodes, %d edges",
            elapsed,
            self._graph.number_of_nodes(),
            edge_count,
        )
        self._save_cache()
        return self._graph

    def get_neighbors(self, skill_name: str) -> list[dict]:
        """Return neighbouring skills sorted by transferability (descending)."""
        skill = self.find_skill(skill_name)
        if skill is None:
            return []

        neighbors = []
        for neighbor_id, edge_data in self._graph[skill["id"]].items():
            node_data = self._graph.nodes[neighbor_id]
            neighbors.append({
                "id": neighbor_id,
                "name": node_data["name"],
                "category": node_data["category"],
                "formality_level": node_data["formality_level"],
                "economic_value": node_data["economic_value"],
                "weight": round(edge_data["weight"], 3),
            })

        return sorted(neighbors, key=lambda x: x["weight"], reverse=True)

    def find_skill(self, name: str) -> Optional[dict]:
        """Find a skill by exact or partial name match. Returns None if not found."""
        key = name.lower().strip()

        if key in self._name_index:
            skill_meta = self._name_index[key]
            return {**skill_meta, "id": skill_meta["id"]}

        # Partial match fallback
        for stored_name, skill_meta in self._name_index.items():
            if key in stored_name or stored_name in key:
                return {**skill_meta, "id": skill_meta["id"]}

        return None

    def get_graph_data(self) -> dict:
        """Return graph as serialisable dict for Pyvis visualisation."""
        nodes = [
            {
                "id": node_id,
                "name": data["name"],
                "category": data["category"],
                "formality_level": data["formality_level"],
                "economic_value": data["economic_value"],
            }
            for node_id, data in self._graph.nodes(data=True)
        ]
        edges = [
            {"source": u, "target": v, "weight": round(data["weight"], 3)}
            for u, v, data in self._graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_seeds(self) -> list[dict]:
        """Load skill seeds from JSON file."""
        with open(_SEED_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _edge_weight(self, s1: dict, s2: dict) -> float:
        """Compute transferability weight between two skills (0.0 – 1.0)."""
        # Keyword overlap (Jaccard on filtered tokens)
        t1 = set(s1["name"].lower().split()) - _STOP_WORDS
        t2 = set(s2["name"].lower().split()) - _STOP_WORDS
        union = t1 | t2
        jaccard = len(t1 & t2) / len(union) if union else 0.0

        # Category score
        if s1["category"] == s2["category"]:
            cat_score = 1.0
        else:
            cat_score = _CATEGORY_WEIGHTS.get(
                (s1["category"], s2["category"]), 0.0
            )

        # Formality proximity — prefer adjacent steps on the path to formality
        f_diff = abs(s1["formality_level"] - s2["formality_level"])
        formality_score = max(0.0, 1.0 - f_diff / 4.0)

        weight = 0.35 * jaccard + 0.35 * cat_score + 0.30 * formality_score
        return round(weight, 4)

    def _is_cache_valid(self) -> bool:
        """Return True if the cache exists and is newer than the seed file."""
        if not _CACHE_FILE.exists() or not _SEED_FILE.exists():
            return False
        return _CACHE_FILE.stat().st_mtime >= _SEED_FILE.stat().st_mtime

    def _save_cache(self) -> None:
        """Persist graph and skill index to disk."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump(
                {
                    "graph": self._graph,
                    "skills": self._skills,
                    "name_index": self._name_index,
                },
                f,
            )
        logger.info("Graph cached to %s", _CACHE_FILE)

    def _load_cache(self) -> None:
        """Restore graph and skill index from disk cache."""
        with open(_CACHE_FILE, "rb") as f:
            data = pickle.load(f)
        self._graph = data["graph"]
        self._skills = data["skills"]
        self._name_index = data["name_index"]
