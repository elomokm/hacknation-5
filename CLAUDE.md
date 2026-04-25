# UNMAPPED — Hack-Nation 5th Global AI Hackathon

## Challenge
Challenge 5: Unmapped — World Bank Youth Summit
"Millions of young people have real skills — the world just has no way to see them."

## Project Vision
UNMAPPED is an open, localizable infrastructure layer that closes the distance between
informal skills and economic opportunity for youth in low/middle-income countries.

**Brief: "Think protocol, not product. Country-specific parameters are CONFIG, not code."**

## Personas
- **Akossiwa**, 22, suburban Cotonou (Bénin) — primary persona. Repairs phones, trades at market.
- **Amara**, 24, Kumasi (Ghana) — secondary persona, pitch reference. Carpentry apprentice.

## 3 Modules

### Module 01 — Skill Extraction & Standardization
Input: free-text description of work (any language, any register)
Process: claude-sonnet-4-5 extracts skills → maps to ESCO taxonomy subset
Output: StandardizedProfile (JSON-LD compatible, portable, offline-exportable)

### Module 02 — Risk Assessment
- Automation risk: Frey-Osborne scores, LMIC-adjusted per country config
- Adjacent skills: NetworkX graph traversal → upskilling pathways
- Projection: Wittgenstein Centre education data by region/year

### Module 03 — Opportunity Matching
- Match StandardizedProfile against local opportunity registry
- Surface ≥2 econometric signals (ILOSTAT wage data, employment share)
- Return ranked results with income delta and pathway steps

## Stack
- Backend: FastAPI + Python 3.12
- LLM: Anthropic claude-sonnet-4-5 (extraction + explanation)
- Graph: NetworkX (adjacent skill traversal)
- Config: YAML per country (runtime-switched, zero code changes)
- Data: ESCO subset, ISCO-08, Frey-Osborne 2017, ILOSTAT, Wittgenstein Centre
- Frontend: Streamlit (mobile-first, low-bandwidth)

## Country-Agnostic Requirement
EVERY country-specific value lives in `configs/{country_code}.yaml`:
- Labor market data file reference
- Currency + USD conversion rate
- Education taxonomy + ISCED mapping
- Automation LMIC calibration factor
- Opportunity types enabled
- UI language + supported scripts

Adding a new country = write one YAML file. No code changes.

## Required Real Data Sources (non-negotiable for jury)
1. **ILOSTAT**: wage by sector, youth unemployment rate, informal employment share
2. **Frey-Osborne 2017**: automation probability by occupation (ISCO-matched)

## Design for Constraint
- Text-first UI: no large images, no CDN-heavy libraries
- Every API response < 5 KB JSON
- Profile exportable as offline JSON
- Works on 3G; tested at mobile viewport

## Strong Submission Checklist
- [ ] ≥2 econometric signals visible to user (wage delta, automation risk %)
- [ ] 2 real country configs switching without code changes (BEN + SEN)
- [ ] Data sources named and URL-linked in UI footnote
- [ ] Honest "limits" section in policymaker view
- [ ] Mobile viewport tested

## Pitch Hook
"Je m'appelle Akossiwa. J'ai 22 ans. Je répare des téléphones à Cotonou.
Je suis compétente. Je suis invisible aux données.
UNMAPPED me voit."

## Git Rules
- No AI/assistant mentions in commit messages
- Conventional commits: feat: / fix: / chore: / refactor: / docs:
- Commit after each working feature — never commit broken code
- One logical change per commit

## Code Rules
- Type hints everywhere
- Pydantic v2 models for all data structures
- No print() — use logging
- Every function has a one-line docstring minimum
- Handle all exceptions explicitly — never let the app crash
- No hardcoded API keys, no TODO comments left in merged code
