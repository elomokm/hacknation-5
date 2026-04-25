# UNMAPPED — Localization Guide

**Adding a new country requires zero Python changes.** Drop 3 files in
`backend/` and call one HTTP endpoint. The country appears across the
API, both dashboards, and the country-toggle in the frontend sidebar.

This is what makes UNMAPPED *infrastructure* and not just an app.

---

## How auto-discovery works

At startup and on demand, `backend/core/config_loader.py` scans
`backend/configs/*.yaml`, reads each file's `country_code` field, and
registers the country. **There is no hardcoded country list.**

```
backend/configs/
├── benin.yaml      → BEN
├── senegal.yaml    → SEN
├── ghana.yaml      → GHA
└── (drop kenya.yaml here → KEN appears after /api/config/reload)
```

---

## Active country configs

| Country | Code | Currency | Languages | LMIC factor | Education ladder |
|---|---|---|---|---|---|
| Bénin | BEN | XOF | fr / fon / en | 0.70 | aucun → primaire → BEPC → Bac → BTS → Licence → Master+ |
| Sénégal | SEN | XOF | fr / wo / en | 0.72 | aucun → primaire → BFEM → Bac → BTS → Licence → Master+ |
| Ghana | GHA | GHS | en / tw / ee / fr | 0.68 | None → Primary → BECE → WASSCE → HND → Bachelor → Master+ |

---

## Step-by-step: add a new country (zero code)

### Step 1 — Drop the labor data file
```
backend/data/ilostat/{code_lower}_labor_2024.json
```

Required fields (matches `LaborMarketData` Pydantic model — see
`backend/core/models.py`):
```json
{
  "country": "...", "country_code": "...", "year": 2024,
  "source": "ILOSTAT", "source_url": "...", "notes": "...",
  "wage_by_sector": [
    {"sector": "...", "median_monthly_xof": 0, "median_monthly_usd": 0}
  ],
  "employment_by_sector": [
    {"sector": "...", "share_pct": 0.0}
  ],
  "youth_unemployment_rate": 0.0,
  "informal_employment_share": 0.0,
  "youth_neet_rate": 0.0
}
```

> Note: the field name is `median_monthly_xof` for Pydantic schema
> compatibility. Values can be in any local currency (GHS for Ghana,
> NGN for Nigeria…). Mention the unit explicitly in `notes`.

### Step 2 — Drop the opportunities file
```
backend/data/opportunities/{code_lower}_opportunities.json
```

Array of opportunities matching the `Opportunity` Pydantic model
(see `backend/core/models.py`). 5–30 entries, each tagged
`realistic_for_youth: true|false`.

### Step 3 — Drop the country YAML
```
backend/configs/{code_lower}.yaml
```

Use `backend/configs/ghana.yaml` as the most recent template.
Required top-level keys: `country`, `country_code`, `ui`, `labor_data`,
`education_taxonomy`, `automation_calibration`, `opportunities`,
`projections`.

The full schema is also queryable at:
```
GET /api/config/schema
```

### Step 4 — Hot-reload (no restart)
```bash
curl -X POST http://localhost:8000/api/config/reload
```

The new country appears immediately in:
- `GET /api/config/countries`
- The Streamlit sidebar toggle
- All `/api/opportunities/{code}/*` and `/api/risk/*` endpoints

---

## Every parameter is configurable per country

| Parameter | YAML location | What it controls |
|---|---|---|
| `country`, `country_code` | root | Display name + ISO code |
| `ui.primary_language` | ui | Default UI language code (ISO 639-1) |
| `ui.supported_languages` | ui | All supported language codes |
| `ui.script` | ui | Writing system (latin, arabic, ethiopic…) |
| `ui.language_display_names` | ui | Code → display name (e.g. `tw: "Twi"`) |
| `labor_data.source_file` | labor_data | Path to ILOSTAT JSON |
| `labor_data.currency` | labor_data | Local currency code |
| `labor_data.usd_conversion_rate` | labor_data | 1 USD = N local |
| `labor_data.isco_to_sector_mapping` | labor_data | ISCO 2-digit → sector label (must match wage_by_sector labels) |
| `labor_data.informal_sector_discount_factor` | labor_data | Informal earn ≈ formal × this (typical 0.40–0.75) |
| `labor_data.high_value_wage_threshold_usd` | labor_data | Sector flagged "high-value" above this |
| `labor_data.growth_strategic_sectors` | labor_data | List of strategic sector labels (policymaker dashboard flag) |
| `education_taxonomy.levels` | education | Local education ladder (ordered) |
| `education_taxonomy.mapping_to_isced` | education | Local label → ISCED 2011 code |
| `education_taxonomy.isced_labels` | education | ISCED code → human-readable label (localised) |
| `automation_calibration.lmic_adjustment_factor` | automation | Frey-Osborne US → LMIC correction |
| `automation_calibration.rationale` | automation | Why this factor was chosen (cited in dashboards) |
| `opportunities.source_file` | opportunities | Path to opportunities JSON |
| `opportunities.types_enabled` | opportunities | Subset of [formal_employment, self_employment, gig, training_pathway] |
| `projections.source_file` | projections | Path to Wittgenstein regional data |

---

## What is NOT configurable per country

These are intentional global protocol decisions — modifying them would
change the algorithm itself, not the country parameters:

- The Pydantic data models (`backend/core/models.py`) — protocol contract
- The LLM extraction prompt (`module_01_skills/extractor.py`) — universal
- The Frey-Osborne scoring formula — applied uniformly with country LMIC factor
- The A* skill graph traversal heuristic — universal
- The matching algorithm structure — universal

**Default fallbacks** for ISCED labels, language display names, and ISCO→sector
mapping live in the Pydantic models so a sparse country YAML still works
(with a logged warning) — but **a complete, accurate country config provides all
of these explicitly**.

---

## Multi-script environments

For Arabic (Morocco, Mauritania): `ui.script: "arabic"` — the Streamlit
frontend applies `direction: rtl` CSS automatically.

For Amharic (Ethiopia): `ui.script: "ethiopic"` — ensure the chosen font
loads on constrained connections.

---

## Verifying a new country end-to-end

```bash
# After dropping the 3 files and calling /api/config/reload:

curl -s http://localhost:8000/api/config/countries | jq -r '.[].code'
# → BEN, SEN, GHA, KEN  (your new country appears)

curl -s http://localhost:8000/api/config/KEN | jq '.country, .labor_data.currency'
# → "Kenya", "KES"

curl -s "http://localhost:8000/api/opportunities/KEN/signals" | jq '.wage'
# → wage signals computed from your kenya_labor_2024.json
```

In the Streamlit frontend, the sidebar country toggle picks up the new
country on the next page reload — no Python changes, no rebuild.
