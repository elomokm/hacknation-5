"""A* pathfinder: routes extracted skills toward the best African opportunity."""

import json
import logging
from pathlib import Path
from typing import Optional

import networkx as nx
from pydantic import BaseModel

from extractor import Skill
from graph_builder import SkillGraph

logger = logging.getLogger(__name__)

_OPP_FILE = Path(__file__).parent / "data" / "opportunities.json"

_STOP_WORDS = {
    "and", "or", "the", "a", "of", "for", "in", "to", "with",
    "basic", "general", "advanced", "junior", "senior",
}

# Cost per formality step when estimating training weeks
_WEEKS_PER_FORMALITY_STEP = {0: 1, 1: 3, 2: 8, 3: 16, 4: 28}


class PathwayStep(BaseModel):
    """A single skill acquisition step on the pathway."""

    skill_to_acquire: str
    reason: str
    resources: list[str]
    estimated_weeks: int


class Pathway(BaseModel):
    """Full economic pathway from current skills to a target opportunity."""

    target_opportunity: dict
    steps: list[PathwayStep]
    total_weeks: int
    confidence: float
    graph_path: list[str]


class AStarPathfinder:
    """Finds optimal skill pathways using A* traversal over the SkillGraph."""

    def __init__(self, skill_graph: SkillGraph) -> None:
        """Initialise with a built SkillGraph instance."""
        self._sg = skill_graph
        self._graph: nx.Graph = skill_graph._graph
        self._opportunities: list[dict] = self._load_opportunities()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_pathway(
        self, skills: list[Skill], target_id: Optional[str] = None
    ) -> Pathway:
        """Find the optimal pathway from the user's skills to a given opportunity.

        If target_id is None, auto-selects the best matching opportunity.
        """
        if target_id is None:
            return self.find_best_opportunity(skills)

        opp = self._get_opportunity(target_id)
        if opp is None:
            raise ValueError(f"Opportunity {target_id!r} not found")

        return self._compute_pathway(skills, opp)

    def find_best_opportunity(self, skills: list[Skill]) -> Pathway:
        """Auto-select the best opportunity and return the full pathway."""
        scored = sorted(
            self._opportunities,
            key=lambda o: self._score_opportunity(skills, o),
            reverse=True,
        )

        # Try top-3 candidates, pick the one with the shortest (most achievable) path
        best_pathway: Optional[Pathway] = None
        for opp in scored[:3]:
            try:
                candidate = self._compute_pathway(skills, opp)
                if best_pathway is None or candidate.total_weeks < best_pathway.total_weeks:
                    best_pathway = candidate
            except Exception as exc:
                logger.debug("Skipping %s: %s", opp["id"], exc)
                continue

        if best_pathway is None:
            # Fallback: return pathway to highest-scored opportunity even if path is trivial
            best_pathway = self._compute_pathway(skills, scored[0])

        return best_pathway

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_opportunities(self) -> list[dict]:
        """Load opportunities from JSON file."""
        with open(_OPP_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _get_opportunity(self, opp_id: str) -> Optional[dict]:
        """Return an opportunity by ID."""
        for opp in self._opportunities:
            if opp["id"] == opp_id:
                return opp
        return None

    def _score_opportunity(self, skills: list[Skill], opp: dict) -> float:
        """Score how well the user's skills align with an opportunity (0–1)."""
        if not skills:
            return 0.0

        user_tokens: set[str] = set()
        for s in skills:
            user_tokens |= self._tokenise(s.name)

        opp_tokens: set[str] = set()
        for req in opp["required_skills"]:
            opp_tokens |= self._tokenise(req)

        overlap = len(user_tokens & opp_tokens) / len(user_tokens | opp_tokens) if opp_tokens else 0.0

        # Bonus for user's average formality being close to (but below) the opportunity
        user_avg_formality = sum(s.level for s in skills) / len(skills)
        opp_formality = opp.get("formality_level", 3)
        formality_gap = max(0.0, opp_formality - user_avg_formality)
        reachability = max(0.0, 1.0 - formality_gap / 5.0)

        return 0.5 * overlap + 0.5 * reachability

    def _compute_pathway(self, skills: list[Skill], opp: dict) -> Pathway:
        """Run A* and build a Pathway for the given opportunity."""
        source_nodes = self._map_skills_to_nodes(skills)
        target_nodes = self._map_requirements_to_nodes(opp["required_skills"])

        if not source_nodes:
            source_nodes = [self._lowest_formality_node()]
        if not target_nodes:
            target_nodes = [self._highest_formality_node()]

        # Filter out targets the user already has
        user_node_ids = {n for n in source_nodes}
        missing_targets = [n for n in target_nodes if n not in user_node_ids]
        if not missing_targets:
            # User already has all required skills
            return self._trivial_pathway(opp, source_nodes)

        raw_path = self._run_astar(source_nodes, missing_targets)
        return self._build_pathway(raw_path, opp, skills)

    def _map_skills_to_nodes(self, skills: list[Skill]) -> list[str]:
        """Map extracted Skill objects to graph node IDs."""
        node_ids: list[str] = []
        for skill in skills:
            node_id = self._best_node_match(skill.name)
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
        return node_ids

    def _map_requirements_to_nodes(self, required_skills: list[str]) -> list[str]:
        """Map opportunity required skill strings to graph node IDs."""
        node_ids: list[str] = []
        for req in required_skills:
            node_id = self._best_node_match(req)
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
        return node_ids

    def _best_node_match(self, name: str) -> Optional[str]:
        """Return the graph node ID that best matches a skill name."""
        tokens = self._tokenise(name)
        best_id: Optional[str] = None
        best_score = -1.0

        for node_id, data in self._graph.nodes(data=True):
            node_tokens = self._tokenise(data["name"])
            union = tokens | node_tokens
            if not union:
                continue
            score = len(tokens & node_tokens) / len(union)
            if score > best_score:
                best_score = score
                best_id = node_id

        return best_id if best_score > 0.0 else None

    def _run_astar(self, sources: list[str], targets: list[str]) -> list[str]:
        """Run A* from the best source to the nearest target; return node ID list."""
        def edge_cost(u: str, v: str, d: dict) -> float:
            """Convert transferability weight to traversal cost."""
            return 1.0 - d.get("weight", 0.5)

        def heuristic(node: str, target: str) -> float:
            """Admissible heuristic: formality distance scaled to edge cost range."""
            f_node = self._graph.nodes[node].get("formality_level", 3)
            f_target = self._graph.nodes[target].get("formality_level", 3)
            # Scale so heuristic never exceeds actual minimum edge cost (≤ 0.82)
            return min(0.8, abs(f_target - f_node) * 0.15)

        best_path: list[str] = []
        best_cost = float("inf")

        for src in sources:
            for tgt in targets:
                if src == tgt:
                    if 0.0 < best_cost:
                        best_path = [src]
                        best_cost = 0.0
                    continue
                if not (self._graph.has_node(src) and self._graph.has_node(tgt)):
                    continue
                try:
                    path = nx.astar_path(
                        self._graph, src, tgt, heuristic=heuristic, weight=edge_cost
                    )
                    cost = sum(
                        edge_cost(path[i], path[i + 1], self._graph[path[i]][path[i + 1]])
                        for i in range(len(path) - 1)
                    )
                    if cost < best_cost:
                        best_cost = cost
                        best_path = path
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

        if not best_path:
            # Graph not connected for this pair — return trivial single-node path
            best_path = [sources[0]]

        return best_path

    def _build_pathway(
        self, path: list[str], opp: dict, skills: list[Skill]
    ) -> Pathway:
        """Convert a graph node path into a human-readable Pathway."""
        graph_path = [self._graph.nodes[n]["name"] for n in path]
        user_node_ids = {self._best_node_match(s.name) for s in skills}

        steps: list[PathwayStep] = []
        for i in range(len(path) - 1):
            current_id = path[i]
            next_id = path[i + 1]
            if next_id in user_node_ids:
                continue  # user already has this skill

            current_data = self._graph.nodes[current_id]
            next_data = self._graph.nodes[next_id]
            edge_w = self._graph[current_id][next_id].get("weight", 0.5)

            f_delta = next_data["formality_level"] - current_data["formality_level"]
            weeks = _WEEKS_PER_FORMALITY_STEP.get(abs(f_delta), 8)

            steps.append(PathwayStep(
                skill_to_acquire=next_data["name"],
                reason=(
                    f"Builds directly on your {current_data['name']} background "
                    f"(transferability {edge_w:.0%}). "
                    f"Moves you from level {current_data['formality_level']} "
                    f"to {next_data['formality_level']} on the formality scale."
                ),
                resources=opp.get("training_resources", [])[:2],
                estimated_weeks=weeks,
            ))

        if not steps:
            steps = self._gap_steps(skills, opp)

        total_weeks = sum(s.estimated_weeks for s in steps)
        confidence = self._path_confidence(path)

        return Pathway(
            target_opportunity=opp,
            steps=steps,
            total_weeks=total_weeks,
            confidence=confidence,
            graph_path=graph_path,
        )

    def _gap_steps(self, skills: list[Skill], opp: dict) -> list[PathwayStep]:
        """Fallback: generate one step per missing required skill."""
        user_tokens: set[str] = set()
        for s in skills:
            user_tokens |= self._tokenise(s.name)

        steps: list[PathwayStep] = []
        for req in opp["required_skills"]:
            req_tokens = self._tokenise(req)
            if not req_tokens & user_tokens:
                steps.append(PathwayStep(
                    skill_to_acquire=req.title(),
                    reason=f"Required by {opp['title']} and not yet in your skill set.",
                    resources=opp.get("training_resources", [])[:2],
                    estimated_weeks=6,
                ))
        return steps or [PathwayStep(
            skill_to_acquire=opp["required_skills"][0].title(),
            reason=f"Core requirement for {opp['title']}.",
            resources=opp.get("training_resources", [])[:2],
            estimated_weeks=4,
        )]

    def _trivial_pathway(self, opp: dict, source_nodes: list[str]) -> Pathway:
        """Return a pathway when user already holds all required skills."""
        graph_path = [self._graph.nodes[n]["name"] for n in source_nodes[:1]]
        return Pathway(
            target_opportunity=opp,
            steps=[],
            total_weeks=0,
            confidence=1.0,
            graph_path=graph_path,
        )

    def _path_confidence(self, path: list[str]) -> float:
        """Compute confidence as harmonic mean of edge weights along the path."""
        if len(path) < 2:
            return 1.0
        weights = [
            self._graph[path[i]][path[i + 1]].get("weight", 0.5)
            for i in range(len(path) - 1)
        ]
        harmonic = len(weights) / sum(1.0 / w for w in weights if w > 0)
        return round(min(1.0, harmonic), 3)

    def _lowest_formality_node(self) -> str:
        """Return the node ID with the lowest formality level."""
        return min(
            self._graph.nodes,
            key=lambda n: self._graph.nodes[n].get("formality_level", 99),
        )

    def _highest_formality_node(self) -> str:
        """Return the node ID with the highest formality level."""
        return max(
            self._graph.nodes,
            key=lambda n: self._graph.nodes[n].get("formality_level", 0),
        )

    @staticmethod
    def _tokenise(text: str) -> set[str]:
        """Lowercase-split text into tokens, removing stop words."""
        return set(text.lower().split()) - _STOP_WORDS
