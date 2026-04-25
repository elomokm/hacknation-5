# UNMAPPED — Localization Guide

Adding a new country requires **one YAML file**. No code changes.

---

## Every Configurable Parameter

| Parameter | Location in YAML | Description |
|---|---|---|
| `country` | root | Display name |
| `country_code` | root | 3-letter ISO code (BEN, SEN, GHA…) |
| `ui.primary_language` | ui | Default UI language (ISO 639-1) |
| `ui.supported_languages` | ui | All supported languages |
| `ui.script` | ui | Writing system (latin, arabic, tifinagh…) |
| `labor_data.source_file` | labor_data | Path to ILOSTAT JSON file |
| `labor_data.currency` | labor_data | Local currency code (XOF, GHS, NGN…) |
| `labor_data.usd_conversion_rate` | labor_data | Current rate (1 USD = N local) |
| `education_taxonomy.levels` | education_taxonomy | Local education ladder (ordered) |
| `education_taxonomy.mapping_to_isced` | education_taxonomy | ISCED-2011 equivalence map |
| `automation_calibration.lmic_adjustment_factor` | automation_calibration | Frey-Osborne US→LMIC correction |
| `automation_calibration.rationale` | automation_calibration | Why this factor was chosen |
| `opportunities.types_enabled` | opportunities | Enabled opportunity types |
| `projections.source_file` | projections | Path to Wittgenstein regional data |

---

## Step-by-Step: How to Add a New Country

### Step 1 — Create the labor data file
```bash
touch backend/data/ilostat/{country_code_lower}_labor_2024.json
```
Populate using ILOSTAT public data: https://ilostat.ilo.org/data/
Required fields: `wage_by_sector`, `employment_by_sector`,
`youth_unemployment_rate`, `informal_employment_share`.

### Step 2 — Create the country YAML config
```bash
cp backend/configs/benin.yaml backend/configs/{country_code_lower}.yaml
```
Update every field. Pay special attention to:
- `education_taxonomy.levels` — use local names, not translated ones
- `automation_calibration.lmic_adjustment_factor` — 0.65–0.80 for most LMICs
- `labor_data.usd_conversion_rate` — use IMF rate for the reference year

### Step 3 — Register in config_loader.py
```python
# In backend/core/config_loader.py, add to _CODE_TO_FILE:
_CODE_TO_FILE = {
    "BEN": "benin",
    "SEN": "senegal",
    "GHA": "ghana",   # ← add this line
}
```
This is the **only code change** required.

### Step 4 — Test
```bash
ACTIVE_COUNTRY=GHA make backend
curl http://localhost:8000/health
# → {"status": "ok", "country": "GHA"}
```

---

## Active Country Configs

### Bénin (BEN) — Active
- Languages: French, Fon, English
- Currency: XOF (CFA Franc West Africa)
- Education: aucun → primaire → BEPC → Bac → BTS → Licence → Master+
- LMIC factor: 0.70
- Data: ILOSTAT Bénin 2022–2024

### Sénégal (SEN) — Active
- Languages: French, Wolof, English
- Currency: XOF (shared with Bénin)
- Education: aucun → primaire → BFEM → Bac → BTS → Licence → Master+
- LMIC factor: 0.72
- Data: ILOSTAT Sénégal 2022–2024

---

## Planned: Ghana (GHA)

**Effort estimate: ~4 hours**

| Task | Time |
|---|---|
| Collect ILOSTAT Ghana data | 1h |
| Write `ghana.yaml` config | 30min |
| Add GHA to config_loader.py | 5min |
| Update education taxonomy (BECE → WASSCE → HND…) | 30min |
| Test end-to-end with Amara persona | 30min |
| Update DATA_SOURCES.md | 15min |

Key differences from Bénin:
- Currency: GHS (Ghana Cedi), not XOF
- Language: English primary, Twi secondary
- Education system: different ladder (BECE, WASSCE, HND, BSc)
- Automation factor: ~0.68 (slightly higher service-sector digitization)

**Pitch reference**: Amara, 24, Kumasi — carpentry apprentice → furniture export coordinator.

---

## Design for Multi-Script Environments

If adding a country with Arabic script (e.g., Morocco, Mauritania):
1. Set `ui.script: "arabic"` in the YAML
2. Streamlit frontend applies `direction: rtl` CSS via `st.markdown`
3. No other code changes needed

If adding Amharic (Ethiopia):
1. Set `ui.script: "ethiopic"`
2. Ensure font loading works in constrained environments (embed subset)

---

## What Is NOT Configurable Per Country

These are global and require code changes to modify:
- The Pydantic data models (`backend/core/models.py`)
- The LLM extraction logic (`module_01_skills/extractor.py`)
- The automation scoring algorithm (`module_02_risk/automation_scorer.py`)
- The matching algorithm (`module_03_opportunity/matcher.py`)

These are intentional constraints — the protocol is universal,
only the parameters are local.
