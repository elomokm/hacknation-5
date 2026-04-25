"""Smoke test for graph_builder — run with: python test_graph_builder.py"""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from graph_builder import SkillGraph

sg = SkillGraph()

# --- Build (cold) ---
t0 = time.time()
G = sg.build_graph()
elapsed = time.time() - t0

assert elapsed < 3.0, f"Build took {elapsed:.2f}s — too slow"
assert G.number_of_nodes() == 150, f"Expected 150 nodes, got {G.number_of_nodes()}"
assert G.number_of_edges() > 0, "Graph has no edges"
print(f"✓ Build: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges in {elapsed:.2f}s")

# --- Build (warm — from cache) ---
sg2 = SkillGraph()
t1 = time.time()
G2 = sg2.build_graph()
cache_time = time.time() - t1
assert cache_time < 1.0, f"Cache load took {cache_time:.2f}s"
print(f"✓ Cache load: {cache_time:.3f}s")

# --- find_skill ---
skill = sg.find_skill("Mobile phone repair")
assert skill is not None, "find_skill returned None"
assert skill["category"] == "Technical"
assert skill["formality_level"] == 2
print(f"✓ find_skill: {skill['name']} (f={skill['formality_level']})")

# --- find_skill partial match ---
skill2 = sg.find_skill("python")
assert skill2 is not None, "Partial match failed"
print(f"✓ Partial match: {skill2['name']}")

# --- get_neighbors ---
neighbors = sg.get_neighbors("Mobile phone repair")
assert len(neighbors) > 0, "No neighbors found"
assert all("weight" in n for n in neighbors)
assert neighbors == sorted(neighbors, key=lambda x: x["weight"], reverse=True)
print(f"✓ get_neighbors: {len(neighbors)} neighbors (top: {neighbors[0]['name']} w={neighbors[0]['weight']})")

# --- get_graph_data ---
data = sg.get_graph_data()
assert "nodes" in data and "edges" in data
assert len(data["nodes"]) == 150
assert len(data["edges"]) == G.number_of_edges()
print(f"✓ get_graph_data: {len(data['nodes'])} nodes, {len(data['edges'])} edges")

# --- Edge weights are in valid range ---
for u, v, d in G.edges(data=True):
    assert 0.0 <= d["weight"] <= 1.0, f"Invalid weight on ({u},{v}): {d['weight']}"
print("✓ All edge weights in [0.0, 1.0]")

print(f"\nOK — graph_builder smoke test passed")
