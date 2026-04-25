# UNMAPPED

**Closing the distance between informal skills and economic opportunity.**

UNMAPPED is a localizable infrastructure layer for youth in low/middle-income countries.
It takes an informal work description ("I repair phones and manage stock on WhatsApp"),
extracts structured skills, assesses automation risk, and returns ranked economic
pathways backed by real labor market data.

---

## Quick Start

```bash
# Install dependencies
make install

# Copy and fill your API key
cp backend/.env.example backend/.env

# Start backend (port 8000)
make backend

# Start frontend (port 8501)
make frontend
```

## Switch Country Config

```bash
ACTIVE_COUNTRY=BEN make backend   # Bénin (default)
ACTIVE_COUNTRY=SEN make backend   # Sénégal
```

No code changes. Only the YAML config switches.

---

## Architecture

```
Input (free text)
      │
      ▼
[ Module 01 ] Skill Extraction + ESCO Mapping   (claude-sonnet-4-5)
      │
      ▼
[ Module 02 ] Risk Assessment                    (Frey-Osborne + NetworkX)
      │  automation risk · adjacent skills · projection
      ▼
[ Module 03 ] Opportunity Matching               (ILOSTAT wage data)
      │  ranked results · income delta · pathway steps
      ▼
StandardizedProfile  ←→  Policymaker Dashboard
```

## Data Sources

| Dataset | Use |
|---|---|
| ESCO v1.2 | Skill taxonomy (~150 skill subset) |
| ISCO-08 | Occupational classification |
| Frey-Osborne 2017 | Automation risk by occupation |
| ILOSTAT 2024 | Wages, employment share, youth unemployment |
| Wittgenstein Centre | Education projections 2025–2035 |

Full provenance: see `DATA_SOURCES.md`.

## Country Configs

| Country | Code | Status |
|---|---|---|
| Bénin | BEN | Active |
| Sénégal | SEN | Active |
| Ghana | GHA | Planned (see LOCALIZATION.md) |

---

## Hackathon Context

Challenge 5 — Unmapped · World Bank Youth Summit
Hack-Nation 5th Global AI Hackathon · April 2026
Solo submission · Elom Okoumassoun
