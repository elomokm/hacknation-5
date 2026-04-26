# UNMAPPED — Submission

> Hack-Nation 5th Global AI Hackathon × World Bank Youth Summit · Challenge 5
> Solo · Elom Okoumassoun · April 2026

## Live demo

- **App**: https://unmapped.streamlit.app
- **API**: https://unmapped-api.onrender.com/docs (Swagger)
- **Code**: https://github.com/elomokm/hacknation-5

## What it does (300 words)

Millions of young people in low- and middle-income countries have real, monetizable
skills — phone repair, tailoring, market analytics, smallholder agriculture — that
formal labor systems cannot see. CVs assume schooling, ATS systems assume English,
job boards assume an internet connection. The result: a young woman in Cotonou who
runs a phone-repair shop and tracks inventory in Excel is, on paper, "unemployed."

UNMAPPED is the **infrastructure layer** that closes that distance. It is not a job
board. It is a country-agnostic protocol that any government, NGO, training provider,
or employer can plug into.

Three modules, exposed as REST endpoints:

1. **Skill Signal** — free-text description (any language, any register) → ESCO-mapped
   StandardizedProfile (JSON-LD, portable, offline-exportable, QR-shareable).
2. **AI Readiness Risk** — Frey-Osborne automation scores LMIC-adjusted per country,
   plus NetworkX graph traversal surfacing adjacent durable skills.
3. **Opportunity Match** — top-k local opportunities ranked against ILOSTAT wage data,
   with two visible econometric signals (current wage estimate, growth-flagged sectors).

## Why it's infrastructure, not a product

Every country-specific value lives in one YAML file (`backend/configs/{code}.yaml`):
labor data file reference, currency, ISCO→sector mapping, education ladder, ISCED
mapping, automation LMIC factor, UI language and script, opportunity types enabled.
Adding a country is **zero code changes** — just a config file, auto-discovered at
runtime, hot-reloadable via `POST /api/config/reload`.

Live proof: 4 countries deployed across 2 regions and 2 scripts — 🇧🇯 Bénin, 🇸🇳 Sénégal,
🇬🇭 Ghana (West Africa, XOF/GHS, latin), and 🇧🇩 Bangladesh (South Asia, BDT, bengali).

## No-code operator onboarding

The "infrastructure" claim is only real if non-engineers can use it. UNMAPPED
ships an **operator console** (third tab in the Streamlit sidebar) where an
NGO field officer or government program manager uploads a 5-column ILOSTAT-aligned
CSV plus 5 metadata fields — country name, ISO-3 code, currency, USD rate, primary
language — and the system generates the YAML config + labor JSON, validates the
output against the Pydantic schema, and hot-reloads the registry. The new country
appears in the sidebar dropdown within ~10 seconds. End-to-end **under 60 seconds,
no developer required**. Demonstrated live with Côte d'Ivoire.

## Stack

FastAPI · Anthropic Claude Sonnet 4.5 · NetworkX · Pydantic v2 · ESCO v1.2 · ISCO-08 ·
Frey-Osborne 2017 · ILOSTAT 2024 · Wittgenstein Centre · Streamlit · PyVis

## Submission constraints honored

- ≥2 econometric signals visible to user (wage delta, growth-flagged sectors)
- 4 country configs switching without code changes
- All data sources cited with URLs in policymaker view footnote
- Mobile viewport tested
- Honest limits documented in policymaker view
