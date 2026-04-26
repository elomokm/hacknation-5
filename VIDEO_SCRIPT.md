# UNMAPPED — Demo video script (60 seconds)

> One-take screencast on https://unmapped.streamlit.app
> Voice over the screen. No edit cuts needed.

---

## Setup before recording

1. Visit https://unmapped.streamlit.app and **wait for cold start to complete** (the
   dyno spins up in 30-50s). Once you see the persona buttons, the API is warm.
2. Open the **Profile** tab once so the skill graph caches its layout.
3. Open https://unmapped-api.onrender.com/docs in a second tab (for the tech beat).
4. Set browser zoom to 90% so the full UI fits in 1080p.

---

## Beat sheet — 60 seconds

| Time | What's on screen | Voice-over (FR or EN) |
|---|---|---|
| **0-5s** | Sidebar visible, country dropdown showing 🇧🇯 Bénin. Cursor over UNMAPPED title. | "Voici Akossiwa, 22 ans, Cotonou. Elle répare des téléphones, gère un inventaire Excel. Sur le papier, elle est invisible." |
| **5-12s** | Click **Akossiwa, 22** persona button. Form fills instantly with French text + BEPC + fr/fon. | "Un clic. UNMAPPED prend sa description en français." |
| **12-18s** | Click **Generate profile**. Progress bar through extract → risk → match. | "Le pipeline tourne en 8 secondes. Extraction de compétences, risque d'automatisation, opportunités locales." |
| **18-30s** | **Profile tab** open. Show the cards-per-ESCO-category layout. Hover one card. | "Ses compétences sont mappées sur ESCO, le standard européen. JSON-LD exportable, partageable en QR. Portable même sans internet." |
| **30-40s** | **Mirror tab**. Show automation risk gauge + adjacent durable skills + recommended next steps. | "Risque d'automatisation calibré pour le Bénin — pas le score US brut. Et trois compétences adjacentes pour rester pertinente." |
| **40-50s** | **Match tab**. Show top-3 opportunities with wage delta + growth-flagged sectors. | "Trois opportunités locales, avec wage delta en XOF et secteurs en croissance — données ILOSTAT 2024." |
| **50-58s** | **Switch country to 🇧🇩 Bangladesh** in sidebar. Page reloads. Show the new banner with BDT + bengali. | "Et zéro code à changer pour passer du Bénin au Bangladesh. South Asia, devise BDT, script bengali. UNMAPPED est une infrastructure, pas un produit." |
| **58-60s** | Cursor on URL bar showing `unmapped.streamlit.app`. | "UNMAPPED. Open. Localizable. Yours." |

---

## Tech beat (separate 60s, optional)

If you record a second video for the tech jury:

| Time | Screen | Script |
|---|---|---|
| **0-10s** | `backend/configs/` directory tree showing 4 YAMLs. | "Quatre YAMLs. Un par pays. Auto-discovery, pas de hard-code." |
| **10-25s** | Open `bangladesh.yaml` — show currency=BDT, script=bengali, lmic_factor=0.65. | "Tout le contexte pays vit dans le YAML. Devise, mapping ISCO→secteurs, calibration LMIC." |
| **25-40s** | Hit `POST /api/config/reload` in Swagger → list returns 4 countries. | "Hot-reload via API. Tu déposes un YAML, tu pings reload, le pays apparaît." |
| **40-55s** | Show `core/config_loader.py` `_discover_configs()` — the 8-line function. | "L'auto-discovery, c'est huit lignes. Pas un framework. Une infrastructure." |
| **55-60s** | Switch to Streamlit, click Bangladesh persona Rashida. | "Et c'est en prod. Streamlit Cloud + Render. Live." |

---

## Key non-negotiables

- Don't pause more than 2s between clicks. Pace = energy.
- Show the **persona buttons** click — that's the wow moment for jury.
- Show the **country switch** at the end — that's the infrastructure proof.
- Voice in FR for World Bank Africa context, EN if pitching to US judges.
- Keep zoom at 90%, 1080p min. No background music.
