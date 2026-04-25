"""Smoke test for pathfinder — run with: python test_pathfinder.py"""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from extractor import Skill
from graph_builder import SkillGraph
from pathfinder import AStarPathfinder

# Hardcoded skills — no API call needed
SKILLS = [
    Skill(name="Mobile phone repair", category="Technical", level=3, confidence=0.92),
    Skill(name="Basic computer use", category="Digital", level=2, confidence=0.85),
    Skill(name="WhatsApp business communication", category="Digital", level=2, confidence=0.78),
]

# --- Setup ---
sg = SkillGraph()
sg.build_graph()
finder = AStarPathfinder(sg)

# --- find_best_opportunity ---
print("\n=== Finding best opportunity ===")
pathway = finder.find_best_opportunity(SKILLS)

opp = pathway.target_opportunity
print(f"Target : {opp['title']}")
print(f"Income : ${opp['avg_monthly_income_usd']}/month")
print(f"Path   : {' → '.join(pathway.graph_path)}")
print(f"Weeks  : {pathway.total_weeks}")
print(f"Conf   : {pathway.confidence:.0%}")
print(f"Steps  : {len(pathway.steps)}")

for i, step in enumerate(pathway.steps, 1):
    print(f"\n  Step {i}: {step.skill_to_acquire}")
    print(f"    Why  : {step.reason[:80]}...")
    print(f"    Time : ~{step.estimated_weeks} weeks")
    if step.resources:
        print(f"    Learn: {step.resources[0]}")

# --- find_pathway with explicit target ---
print("\n=== Explicit target: IT Support Specialist (opp_010) ===")
pw2 = finder.find_pathway(SKILLS, target_id="opp_010")
print(f"Path   : {' → '.join(pw2.graph_path)}")
print(f"Weeks  : {pw2.total_weeks} | Confidence: {pw2.confidence:.0%}")
print(f"Steps  : {len(pw2.steps)}")

# --- Assertions ---
assert len(pathway.steps) >= 1, "Pathway must have at least one step"
assert pathway.confidence > 0, "Confidence must be > 0"
assert pathway.total_weeks >= 0
assert isinstance(pathway.graph_path, list) and len(pathway.graph_path) >= 1
assert "title" in pathway.target_opportunity
for step in pathway.steps:
    assert step.estimated_weeks > 0
    assert step.skill_to_acquire
    assert step.reason

print("\nOK — pathfinder smoke test passed")
