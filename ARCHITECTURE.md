# UNMAPPED — Architecture

## Design Principle

Country-specific parameters are CONFIG, not code.
Every deployment variable lives in `backend/configs/{country_code}.yaml`.
Switching from Bénin to Sénégal requires no code changes.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    UNMAPPED Backend                      │
│                                                         │
│  ┌──────────────┐   ┌────────────────────────────────┐  │
│  │ Config Layer │   │         API (FastAPI)           │  │
│  │              │   │  POST /analyze                  │  │
│  │ benin.yaml   │──▶│  GET  /health                   │  │
│  │ senegal.yaml │   │  GET  /opportunities/{country}  │  │
│  └──────────────┘   └────────────┬───────────────────┘  │
│                                  │                       │
│              ┌───────────────────┼──────────────────┐    │
│              │                   │                  │    │
│              ▼                   ▼                  ▼    │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  Module 01    │  │   Module 02     │  │  Module 03   ││
│  │  Skills       │  │   Risk          │  │  Opportunity ││
│  │               │  │                 │  │  Matching    ││
│  │ extractor.py  │  │ automation_     │  │ matcher.py   ││
│  │ taxonomy_     │  │ scorer.py       │  │ econometrics ││
│  │ mapper.py     │  │ adjacent_       │  │ .py          ││
│  │ profile_      │  │ skills.py       │  │ opportunities││
│  │ generator.py  │  │ projection_     │  │ .py          ││
│  └───────┬───────┘  │ loader.py       │  └──────┬───────┘│
│          │          └────────┬────────┘         │        │
│          │                   │                  │        │
│          └───────────────────┼──────────────────┘        │
│                              │                           │
│                     ┌────────▼────────┐                  │
│                     │   Data Layer    │                  │
│                     │                 │                  │
│                     │ esco/           │                  │
│                     │ isco/           │                  │
│                     │ frey_osborne/   │                  │
│                     │ ilostat/        │                  │
│                     │ wittgenstein/   │                  │
│                     └─────────────────┘                  │
└─────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
    ┌─────────▼──────────┐       ┌────────────▼────────┐
    │   Youth View       │       │  Policymaker View   │
    │                    │       │                     │
    │ · Skill profile    │       │ · Aggregate stats   │
    │ · Risk score       │       │ · Skill gap map     │
    │ · Opportunities    │       │ · Automation trends │
    │ · Pathway steps    │       │ · Data sources      │
    └────────────────────┘       └─────────────────────┘
```

---

## Module Details

### Module 01 — Skill Extraction & Standardization

```
Input: raw text (any language)
  └─▶ claude-sonnet-4-5 extraction prompt
       └─▶ list[RawSkill] with confidence scores
            └─▶ taxonomy_mapper.py → ESCO IDs
                 └─▶ profile_generator.py → StandardizedProfile (JSON-LD)
```

### Module 02 — Risk Assessment

```
StandardizedProfile
  └─▶ automation_scorer.py
       └─▶ Frey-Osborne lookup by ISCO match
            └─▶ × lmic_adjustment_factor (from country config)
                 └─▶ RiskAssessment

  └─▶ adjacent_skills.py
       └─▶ NetworkX graph over ESCO skill graph
            └─▶ BFS/weighted traversal for upskilling paths

  └─▶ projection_loader.py
       └─▶ Wittgenstein data filtered by region + year
```

### Module 03 — Opportunity Matching

```
StandardizedProfile + RiskAssessment
  └─▶ matcher.py
       └─▶ skill overlap score per opportunity
            └─▶ econometrics.py
                 └─▶ ILOSTAT wage signal (income delta)
                      └─▶ MatchResult with ranked list
```

---

## Config Switching

```python
# No code change needed — set env var before start
ACTIVE_COUNTRY=BEN  # or SEN, GHA, ...

# config_loader.py resolves:
# BEN → backend/configs/benin.yaml
# SEN → backend/configs/senegal.yaml
```

## Data Flow Types

```
str (raw text)
  → StandardizedProfile
    → RiskAssessment
      → list[MatchResult]
        → HTTP response JSON
```

All types are Pydantic v2 models defined in `backend/core/models.py`.
