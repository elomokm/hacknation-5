# Traji — Hack-Nation 5th Global AI Hackathon

## Challenge
Challenge 5 : Unmapped — World Bank
"Millions of young people have real skills — the world just has no way to see them."

## MVP Goal
Build an AI system that takes informal skill descriptions (text or image)
and returns the optimal economic pathway from informality to formal opportunity —
using a mathematically grounded skill graph with A* pathfinding.

## The Differentiating Insight
This is NOT a matching problem. It's a graph traversal problem.
Informal skills are particles in a metastable high-energy state.
We find the minimum activation path toward economic equilibrium.
The graph structure is LEARNED from African job market data,
not hardcoded — edges emerge from co-occurrence + spectral decomposition.

## Architecture
- Input: text description or image of work (GPT-4o vision)
- Skill Extraction: structured skill list with confidence scores
- Graph: NetworkX weighted graph (500 nodes, learned edges)
- Pathfinding: A* with embedding-based heuristic
- Impact Score: ROI économique estimé du chemin
- Frontend: Streamlit with live Pyvis graph visualization

## Stack
- Backend: FastAPI + Python 3.12
- LLM: OpenAI GPT-4o (vision + text)
- Embeddings: OpenAI text-embedding-3-small
- Graph: NetworkX + spectral layout
- Visualization: Pyvis (interactive graph)
- Frontend: Streamlit

## Team
- Elom Okoumassoun : ML/CV Engineer — full stack solo

## Constraints
- 24h hackathon — solo
- Demo Video : 60 sec max
- Tech Video : 60 sec max
- Deadline: Sunday April 26, 9:00 AM ET
- Submit on: projects.hack-nation.ai

## Priority Order
1. Skill extraction working (extractor.py)
2. Graph built and navigable (graph_builder.py)
3. A* pathfinding returning a real path (pathfinder.py)
4. Impact score calculated (impact_scorer.py)
5. Streamlit demo showing live graph + pathway
6. Project summary written
7. Both videos recorded

## Non-goals (mention in pitch, don't build)
- P2P trust network
- WhatsApp voice interface
- Real-time graph learning from users
- Mobile app

## Pitch Hook
"I grew up in Benin. I know people like this.
I am, in some ways, this person.
Traji finds the path they were never shown."

## Claude Code Rules

### Git
- NEVER mention Claude, AI, or any assistant in commit messages
- Commit messages must follow conventional commits:
  feat: / fix: / chore: / refactor: / docs:
- Commit after each working feature — never commit broken code
- One logical change per commit

### Code Style
- Type hints everywhere
- Pydantic models for all data structures
- No print() — use logging
- Every function has a docstring (one line minimum)
- Handle all exceptions explicitly — never let the app crash

### Workflow
- Build one file at a time
- Verify it works before moving to the next
- Never anticipate next tasks
- If something is unclear, ask before implementing

### Forbidden
- No hardcoded API keys
- No TODO comments left in code
- No unused imports
- No mock data presented as real in the demo