# UNMAPPED

**Closing the distance between informal skills and economic opportunity.**

UNMAPPED is a localizable infrastructure layer for youth in low/middle-income countries.
It takes an informal work description ("I repair phones and manage stock on WhatsApp"),
extracts structured skills, assesses automation risk, and returns ranked economic
pathways backed by real labor market data.

---

## Quick Start

```bash
make install                                   # one-time setup
cp backend/.env.example backend/.env           # add your ANTHROPIC_API_KEY
make dev                                       # API on :8000 + Streamlit on :8501
```

Or run them separately:

```bash
make api          # FastAPI on :8000  (docs at http://localhost:8000/docs)
make frontend     # Streamlit on :8501
make test         # API integration tests
```

## Switch Country

```bash
ACTIVE_COUNTRY=BEN make api    # Bénin (default)
ACTIVE_COUNTRY=SEN make api    # Sénégal
```

Or live in the Streamlit sidebar (🇧🇯 Bénin ↔ 🇸🇳 Sénégal). No code changes.

---

## API Usage

UNMAPPED is **infrastructure**, not a product. Every module is exposed via REST.
Open by design: any government, NGO, training provider, or employer can plug in.

**OpenAPI docs:** http://localhost:8000/docs
**Operator integration guide:** see [INTEGRATION.md](INTEGRATION.md) — how to push your own opportunities (ANPE, BRAC, GIPC, ATS systems, etc.) and consume the dashboards. (Swagger UI)

```bash
# Health
curl http://localhost:8000/api/health

# List supported countries with metadata (the localizability proof)
curl http://localhost:8000/api/config/countries

# Generate a full StandardizedProfile (JSON-LD)
curl -X POST http://localhost:8000/api/profile/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Akossiwa",
    "text": "Je répare des téléphones depuis 4 ans à Cotonou.",
    "education_level": "BEPC",
    "languages": ["fr", "fon"],
    "country_code": "BEN"
  }'

# Match a stored profile to local opportunities
curl -X POST http://localhost:8000/api/opportunities/match \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "<id-from-above>", "country_code": "BEN", "top_k": 5}'

# Population-level econometric signals (no profile needed)
curl http://localhost:8000/api/opportunities/BEN/signals
```

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Liveness + active country |
| `GET /api/info` | Modules, data sources, supported countries |
| `GET /api/config/countries` | All countries + their metadata |
| `GET /api/config/{code}` | Full CountryConfig for one country |
| `GET /api/config/schema` | JSON schema + how-to-add-a-country guide |
| `POST /api/profile/extract` | Extracted + mapped skills (no profile) |
| `POST /api/profile/generate` | Full StandardizedProfile (JSON-LD) |
| `GET /api/profile/{id}/jsonld` | Profile served as `application/ld+json` |
| `POST /api/risk/assess` | RiskAssessment + adjacent durable skills |
| `GET /api/risk/projections/{code}` | Wittgenstein education trajectory |
| `POST /api/opportunities/match` | Top-k matches + 2 econometric signals |
| `GET /api/opportunities/{code}/signals` | Wage + sector growth signals |
| `GET /api/opportunities/{code}/dashboard/youth` | Composite youth dashboard |
| `GET /api/opportunities/{code}/dashboard/policymaker` | Country aggregate dashboard |
| `GET /api/opportunities/{code}` | List all opportunities for a country |
| `POST /api/opportunities/{code}/upsert` | **Operator ingestion**: add/replace one opportunity |
| `POST /api/opportunities/{code}/bulk` | **Operator ingestion**: atomic batch upsert |
| `DELETE /api/opportunities/{code}/{opp_id}` | **Operator ingestion**: remove one opportunity |

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
