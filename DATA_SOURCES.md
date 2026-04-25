# UNMAPPED — Data Sources

All data used in UNMAPPED is sourced from public datasets. This document is the authoritative
record of provenance, subset selection, and any estimation or transformation applied.

---

## 1. ESCO — European Skills, Competences, Qualifications and Occupations

**File:** `backend/data/esco/skills_subset.json`
**Source:** ESCO v1.2 — European Commission
**URL:** https://esco.ec.europa.eu/en/use-esco/download
**Licence:** Creative Commons Attribution 4.0 (CC BY 4.0)

**What it is:** ESCO is the European multilingual classification of occupations, skills,
competences and qualifications. It contains ~13,890 skills/competences.

**What we did:**
- Selected 150 skills relevant to the West African informal economy and its formal pathways
- Coverage: phone repair, web development, digital literacy, carpentry, welding, tailoring,
  driving, hospitality, agriculture, commerce, healthcare, and formal economy targets
- IDs use simplified format `esco:skill:XXXX` instead of full UUID URIs
- Full ESCO URIs follow the pattern: `http://data.europa.eu/esco/skill/{uuid}`
- Descriptions are representative of ESCO preferred label definitions

**Honest limit:** Our IDs are simplified sequential codes, not the actual ESCO UUIDs.
The labels and categories are faithful to real ESCO taxonomy groupings.

---

## 2. ISCO-08 — International Standard Classification of Occupations

**File:** `backend/data/isco/isco_08_groups.json`
**Source:** International Labour Organization (ILO)
**URL:** https://www.ilo.org/public/english/bureau/stat/isco/isco08/index.htm
**Licence:** Free for non-commercial use

**What it is:** ISCO-08 is the ILO's standard classification of occupations into a set of
clearly defined groups. We use the 2-digit major and sub-major group level (39 entries).

**What we did:**
- Included all 39 real 2-digit ISCO-08 groups with official titles
- Added 1-sentence descriptions based on official ILO group descriptions

**Honest limit:** Descriptions are paraphrased from official ILO documentation,
not verbatim copies. Full official descriptions available at the source URL.

---

## 3. Frey-Osborne — Automation Risk Scores

**File:** `backend/data/frey_osborne/automation_scores.json`
**Source:** Frey, C.B. & Osborne, M.A. (2013/2017). "The Future of Employment:
How susceptible are jobs to computerisation?" Oxford Martin School Working Paper.
**URL:** https://www.oxfordmartin.ox.ac.uk/downloads/academic/The_Future_of_Employment.pdf
**Licence:** Academic research paper, cited with attribution

**What it is:** The Frey-Osborne study estimated automation probability for 702 US
occupations using a machine learning model trained on O*NET task data. The 2017 version
updated methodology.

**What we did:**
- Selected 50 occupations most relevant to LMIC/West Africa labour markets
- Mapped each occupation to its closest ISCO-08 2-digit group code
- Preserved exact automation probabilities from the published paper
- All values are directly from Table 1 of the paper or supplementary data

**LMIC Adjustment (applied at runtime, not in raw data):**
The raw Frey-Osborne probabilities reflect US occupation task structures. UNMAPPED applies
a country-configurable `lmic_adjustment_factor` (0.70 for Bénin, 0.72 for Sénégal) at
runtime. Rationale: LMIC economies have higher shares of manual, non-routine tasks and
lower capital substitution rates. This is consistent with World Bank methodology for
applying automation risk in developing country contexts (World Bank Development Report 2019).

**Honest limit:** Frey-Osborne was calibrated on US O*NET data. Its applicability to
West African occupation task compositions is imperfect. The LMIC factor is a pragmatic
correction, not a validated empirical calibration for Bénin or Sénégal specifically.

---

## 4. ILOSTAT — Bénin Labour Market Data

**File:** `backend/data/ilostat/benin_labor_2024.json`
**Source:** ILOSTAT — ILO Department of Statistics
**URL:** https://ilostat.ilo.org/data/
**Primary national source:** INSAE — Institut National de la Statistique et de l'Analyse
Économique du Bénin. Enquête Modulaire Intégrée sur les Conditions de Vie des Ménages (EMICoV).
**Licence:** Free for non-commercial use

**What we did:**
- Compiled median monthly wages by sector (XOF and USD)
- Compiled employment share by sector
- Used youth unemployment rate, NEET rate, and informal employment share from ILOSTAT
- USD conversion at 600 XOF/USD (IMF 2024 average reference rate)

**Data quality notes:**
- Wage figures are median monthly estimates; actual distributions are wide
- Agriculture wages reflect a mix of subsistence and market-oriented farming
- ICT and Finance wages reflect Cotonou urban formal sector; national coverage is limited
- Reference period: 2022-2024 (most recent available ILOSTAT data for Bénin)

**Honest limit:** Bénin's statistical infrastructure is limited. Some figures,
particularly for informal sector wages, are estimates based on household survey
extrapolation rather than payroll data. Informal employment share (88.3%) is
consistent with ILO 2023 global estimates for Bénin.

---

## 5. ILOSTAT — Sénégal Labour Market Data

**File:** `backend/data/ilostat/senegal_labor_2024.json`
**Source:** ILOSTAT — ILO Department of Statistics
**URL:** https://ilostat.ilo.org/data/
**Primary national source:** ANSD — Agence Nationale de la Statistique et de la Démographie.
Enquête sur l'Emploi au Sénégal (EES 2023).
**Licence:** Free for non-commercial use

**What we did:** Same methodology as Bénin file. Sénégal figures reflect
a slightly more formalized economy (Plan Sénégal Émergent context) and
higher Dakar urban wage premium.

**Honest limit:** National medians mask significant Dakar/interior wage gaps.
ICT and Finance figures are heavily influenced by Dakar's formal sector.
Informal employment share (76.1%) is lower than Bénin due to larger formal
public sector (Plan Sénégal Émergent).

---

## 6. Wittgenstein Centre — West Africa Education Projections

**File:** `backend/data/wittgenstein/projections_west_africa.json`
**Source:** Wittgenstein Centre for Demography and Global Human Capital
**URL:** https://www.wittgensteincentre.org/dataexplorer
**Licence:** Free for research and educational use

**What it is:** The Wittgenstein Centre produces population projections disaggregated
by age, sex, and educational attainment for all countries to 2100. SSP2 is the
"medium" scenario (Shared Socioeconomic Pathway 2).

**What we did:**
- Used SSP2 (medium scenario) projections for West Africa region
- Aggregated 16 ECOWAS member state projections to regional level
- Focused on youth population aged 15-29
- Extracted 6-year intervals from 2025 to 2035
- 6 education levels: No education, Primary incomplete, Primary complete,
  Lower secondary, Upper secondary, Post-secondary

**Honest limit:** These are regional aggregates, not Bénin or Sénégal-specific values.
Country-specific Wittgenstein data would require individual country extraction.
The figures are directionally correct for the sub-region but should not be cited
for country-specific policy without using the country-level data from the source.

---

## Summary Table

| File | Source | Records | Full data? |
|---|---|---|---|
| esco/skills_subset.json | ESCO v1.2 | 150 skills | Subset (150/13,890) |
| isco/isco_08_groups.json | ISCO-08 ILO | 39 groups | Complete (2-digit level) |
| frey_osborne/automation_scores.json | Frey-Osborne 2017 | 50 occupations | Subset (50/702) |
| ilostat/benin_labor_2024.json | ILOSTAT/INSAE | 14 sectors | Estimated from survey data |
| ilostat/senegal_labor_2024.json | ILOSTAT/ANSD | 15 sectors | Estimated from survey data |
| wittgenstein/projections_west_africa.json | Wittgenstein Centre | 36 data points | Regional aggregate, 2025–2035 |

---

*Last updated: April 2026 — Hack-Nation 5th Global AI Hackathon submission*
