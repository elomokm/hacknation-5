# UNMAPPED — Operator Integration Guide

> *"Plug your existing opportunity data into UNMAPPED in 1 day. We standardize,
> match, and surface the econometric reality. You bring the ground truth."*

This guide is for **operators**: governments, NGOs, training providers,
employers, and labor market institutions that already have opportunity data
and want to give their youth (or aggregate it for policymakers) the UNMAPPED
intelligence layer on top.

UNMAPPED is **infrastructure**, not a job board. We don't source opportunities
— you do. We turn what you have into a portable skills profile, an honest
automation-risk assessment, and a realistic match list, in your country's
language, currency, and education taxonomy.

---

## What UNMAPPED provides vs what you bring

| You bring | UNMAPPED provides |
|---|---|
| A list of opportunities (your jobs, your training programs, your gigs) | ESCO/ISCO standardization of skills |
| One country YAML config (one-time setup) | Frey-Osborne LMIC-adjusted automation risk |
| Periodic data refresh (manual, batch, or webhook) | Adjacent durable skill discovery (NetworkX graph) |
|  | Realistic matching (no aspirational "you could be a software engineer") |
| | 2 econometric signals (wage mirror + sector employment) |
| | JSON-LD portable profile + dual dashboard (youth + policymaker) |

---

## The end-to-end pipeline

```
┌────────────────────────────────────────────────────────────────┐
│  YOU: Your existing opportunity database                       │
│   ANPE Bénin Oracle SQL · BRAC weekly CSV from loan officers   │
│   GIZ ProDIJ REST API · Ministry training catalogue            │
│   WhatsApp Business intake · NGO field officer submissions     │
└────────────────────────────────────────────────────────────────┘
                            │
                            │ One ETL adapter — ~1 day to write
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  UNMAPPED INGESTION ENDPOINTS                                  │
│   POST /api/opportunities/{country}/upsert     (1 at a time)   │
│   POST /api/opportunities/{country}/bulk       (batch)         │
│   DELETE /api/opportunities/{country}/{id}     (remove)        │
│   GET /api/opportunities/{country}             (list current)  │
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  UNMAPPED CORE (zero work for you)                             │
│   Module 01 — extract skills (claude-sonnet-4-5 + ESCO)        │
│   Module 02 — risk assessment (Frey-Osborne + LMIC factor)     │
│   Module 03 — match + econometric signals (ILOSTAT)            │
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  YOU CONSUME (any subset, any UI)                              │
│   GET /api/opportunities/{country}/dashboard/youth             │
│   GET /api/opportunities/{country}/dashboard/policymaker       │
│   GET /api/profile/{id}/jsonld   (portable across borders)     │
│   POST /api/risk/assess          (per-profile risk lens)       │
└────────────────────────────────────────────────────────────────┘
```

---

## Step 1 — Country onboarding (one-time, ~2 hours)

If your country isn't listed at `GET /api/config/countries`, add it:

1. Drop `backend/configs/{code_lower}.yaml` (see `LOCALIZATION.md`)
2. Drop `backend/data/ilostat/{code_lower}_labor_2024.json`
3. Drop `backend/data/opportunities/{code_lower}_opportunities.json` (can start empty: `[]`)
4. `curl -X POST http://your-unmapped-host/api/config/reload`

That's it. Your country appears across the API, both dashboards, and the
country-toggle in the frontend. **No Python edits.**

Currently active: BEN, SEN, GHA, BGD.

---

## Step 2 — The Opportunity schema

Every opportunity you push must match this Pydantic shape (see
`backend/core/models.py:Opportunity` for the canonical definition):

```json
{
  "id": "anpe_2024_001234",
  "type": "formal_employment",
  "title": "Junior IT Support Technician",
  "title_local": "Technicien Support Informatique Junior",
  "sector": "Information and communication (ICT)",
  "required_skills_isco": ["25"],
  "required_skills_esco": ["esco:skill:0045"],
  "education_min": "BEPC",
  "experience_years_min": 1,
  "wage_range_xof": [80000, 130000],
  "geography": "Cotonou",
  "remote_eligible": false,
  "description": "Provide first-line IT support for a Cotonou-based NGO.",
  "training_url": null,
  "realistic_for_youth": true
}
```

**Field rules:**

- `id` — your stable identifier (we upsert by this). Use a prefix like `anpe_`, `brac_`, `gipc_` to namespace by source.
- `type` — one of: `formal_employment`, `self_employment`, `gig`, `training_pathway`. Country YAML controls which types are enabled.
- `sector` — must match a sector label in your country's `labor_data` JSON (so wage/employment signals work). Get the list via `GET /api/config/{code}` → `labor_data.isco_to_sector_mapping`.
- `required_skills_isco` — list of 2-digit ISCO-08 codes. See `backend/data/isco/isco_08_groups.json`.
- `required_skills_esco` — list of ESCO skill IDs from our subset. See `backend/data/esco/skills_subset.json`.
- `education_min` — one of your country's education levels. Get the list via `GET /api/config/{code}` → `education_taxonomy.levels`.
- `wage_range_xof` — `[min, max]` monthly. Field name is `wage_range_xof` for schema compat; **values are in your country's local currency** (XOF for BEN/SEN, GHS for GHA, BDT for BGD…).
- `realistic_for_youth` — **honesty flag**. `true` if a 22-year-old with informal background can plausibly access this. UNMAPPED's matcher filters to `true` only — no aspirational matching, per the brief.

OpenAPI schema is also live at `GET /openapi.json` and Swagger UI at `/docs`.

---

## Step 3 — Pushing your data

### Push one opportunity (event-driven, e.g. NGO submits a new job)

```bash
curl -X POST http://localhost:8000/api/opportunities/BEN/upsert \
  -H "Content-Type: application/json" \
  -d @opportunity.json
```

Response:
```json
{
  "country_code": "BEN",
  "inserted": 1,
  "updated": 0,
  "deleted": 0,
  "total_in_country": 31,
  "note": "Per-country caches invalidated. Next /match call will use fresh data."
}
```

Upsert is **idempotent by `id`**: same id = update, new id = insert. Safe to retry.

### Push a batch (periodic ETL, e.g. daily ANPE pull)

```bash
curl -X POST http://localhost:8000/api/opportunities/BEN/bulk \
  -H "Content-Type: application/json" \
  -d '{"opportunities": [opp1, opp2, opp3, ...]}'
```

Atomic — either all opportunities validate or none are written.

### Remove an opportunity (e.g. position filled)

```bash
curl -X DELETE http://localhost:8000/api/opportunities/BEN/anpe_2024_001234
```

Returns 404 if the id doesn't exist — safe to use for cleanup scripts.

### List current state (for diff or audit)

```bash
curl http://localhost:8000/api/opportunities/BEN
```

---

## Step 4 — Consume the intelligence layer

Now that your opportunities are in, your operators can call the
intelligence endpoints — same for every country:

```bash
# Generate a youth profile (LLM extraction + ESCO mapping + JSON-LD)
curl -X POST http://localhost:8000/api/profile/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Akossiwa",
    "text": "Je répare des téléphones depuis 4 ans à Cotonou...",
    "education_level": "BEPC",
    "languages": ["fr", "fon"],
    "country_code": "BEN"
  }'
# → returns full StandardizedProfile + profile_id

# Match against YOUR opportunity registry
curl -X POST http://localhost:8000/api/opportunities/match \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "<id>", "country_code": "BEN", "top_k": 5}'
# → ranked OpportunityMatch list (only realistic_for_youth=true)
#   + wage signal + sector growth signal

# Composite youth dashboard (everything above in one call)
curl "http://localhost:8000/api/opportunities/BEN/dashboard/youth?profile_id=<id>"

# Policymaker aggregate dashboard (no profile needed)
curl http://localhost:8000/api/opportunities/BEN/dashboard/policymaker
```

---

## Reference adapters (writing your own ETL)

A reference adapter is just a Python script (or any HTTP client) that:
1. Reads from your source (SQL, CSV, REST API, WhatsApp webhook…)
2. Maps fields to the UNMAPPED `Opportunity` schema
3. POSTs to `/api/opportunities/{country}/bulk` (or upsert one at a time)

**Example adapter shapes:**

| Operator | Source | Adapter shape | Trigger |
|---|---|---|---|
| ANPE Bénin | Oracle SQL | Cron Python script: SQL → JSON → bulk upsert | Daily |
| BRAC Bangladesh | Field officer CSV | Email parse + Pandas → bulk upsert | Weekly |
| GIZ ProDIJ | REST API | Webhook listener → upsert per event | Event-driven |
| Cotonou NGO | WhatsApp Business | WhatsApp webhook → form fill → upsert | Event-driven |
| GIPC Ghana | Public job board | BeautifulSoup scrape → bulk upsert | Daily |

**Pseudo-code for any adapter:**

```python
import requests

UNMAPPED_API = "http://localhost:8000/api"
COUNTRY = "BEN"

def fetch_from_my_source() -> list[dict]:
    """Your ETL logic — pull from SQL, CSV, REST API, etc."""
    ...

def transform_to_unmapped(raw_record: dict) -> dict:
    """Map your fields to UNMAPPED's Opportunity schema."""
    return {
        "id": f"anpe_{raw_record['ref_id']}",
        "type": "formal_employment",
        "title": raw_record["job_title_en"],
        "title_local": raw_record["job_title_fr"],
        "sector": map_sector(raw_record["industry_code"]),
        "required_skills_isco": [raw_record["isco_2digit"]],
        "required_skills_esco": [],  # optional
        "education_min": raw_record["min_education"],
        "experience_years_min": raw_record["min_experience"] or 0,
        "wage_range_xof": [raw_record["wage_min"], raw_record["wage_max"]],
        "geography": raw_record["city"],
        "remote_eligible": raw_record["remote"] == "Y",
        "description": raw_record["description"][:500],
        "training_url": None,
        "realistic_for_youth": is_youth_accessible(raw_record),
    }

def push():
    raw = fetch_from_my_source()
    payload = {"opportunities": [transform_to_unmapped(r) for r in raw]}
    r = requests.post(f"{UNMAPPED_API}/opportunities/{COUNTRY}/bulk", json=payload)
    r.raise_for_status()
    print(r.json())  # → {"inserted": N, "updated": M, "total_in_country": ...}

if __name__ == "__main__":
    push()
```

---

## Production considerations (out of scope for the hackathon prototype)

The current API is **open by design** — any HTTP client can read or write.
This is intentional for the hackathon (so the jury can `curl` end-to-end),
but production deployments **MUST** add:

- **Authentication**: API keys per operator (e.g. `Authorization: Bearer anpe_<token>`)
- **Authorization**: per-operator namespacing (ANPE can't delete BRAC opportunities even if both push to the same country)
- **Rate limiting**: per-operator quotas
- **Audit log**: who pushed what when (compliance + dispute resolution)
- **Persistent storage**: today opportunities live in JSON files on disk — production should back this with PostgreSQL or similar
- **Observability**: Sentry / OpenTelemetry for ingestion errors

These are standard FastAPI add-ons (`fastapi-auth`, `slowapi`, `sqlalchemy`)
and don't require touching the core modules. The protocol is stable.

---

## What is and isn't UNMAPPED's responsibility

✅ **UNMAPPED owns:**
- The standardization layer (ESCO/ISCO/Frey-Osborne/ILOSTAT)
- The skill extraction algorithm (LLM + taxonomy mapping)
- The risk model (LMIC-adjusted Frey-Osborne)
- The matching algorithm (realistic, no aspirational)
- The econometric signals presentation (wage mirror, sector employment)
- The dual dashboard (youth + policymaker)
- The country config schema and validation

❌ **UNMAPPED does NOT own:**
- Your source of opportunities (you have it; we don't replace it)
- Your authentication / user management (your platform handles it)
- Your front-end (use our Streamlit demo, embed our widgets, or build your own — JSON-LD profile + REST API are the contract)
- The legal liability of matching (we surface signals, you make decisions)

This separation is **the value proposition** — UNMAPPED runs in front of any
existing labor market system without forcing a rebuild. One day of operator
integration vs. eighteen months of building the standardization layer from scratch.

---

## Help

OpenAPI Swagger docs : `http://localhost:8000/docs`
Schema introspection : `GET /api/config/schema`
Country list : `GET /api/config/countries`
Health check : `GET /api/health`
