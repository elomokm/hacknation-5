"""Module 02 — Adjacent skill discovery via NetworkX graph. Implemented in Phase 2."""

import logging

import networkx as nx

logger = logging.getLogger(__name__)


def build_skill_graph(esco_skills: list[dict]) -> nx.Graph:
    """Build a weighted NetworkX graph over ESCO skills.

    Edges represent skill transferability. Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2")


def find_adjacent_skills(graph: nx.Graph, skill_ids: list[str], depth: int = 2) -> list[str]:
    """Return adjacent skill IDs reachable within given graph depth.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2")
