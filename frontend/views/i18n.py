"""UI internationalization — single dict per locale, t(key) lookup.

Locale is held in st.session_state["ui_lang"] (default "en"), driven by
the sidebar toggle. Use t("key") everywhere instead of hardcoded strings.

Note on scope: this covers UI chrome (labels, headings, buttons, captions).
LLM-generated content (profile_summary, next_steps from the API) keeps the
language of the persona's input — that's by design (the user's narrative
must stay in their language).
"""

import streamlit as st

DEFAULT_LANG = "en"
SUPPORTED = ["en", "fr"]

_STRINGS: dict[str, dict[str, str]] = {
    # ── Sidebar ──────────────────────────────────────────────────
    "sidebar.title": {
        "en": "UNMAPPED",
        "fr": "UNMAPPED",
    },
    "sidebar.subtitle": {
        "en": "World Bank × Hack-Nation 5",
        "fr": "World Bank × Hack-Nation 5",
    },
    "sidebar.country": {
        "en": "Active country",
        "fr": "Pays actif",
    },
    "sidebar.interface": {
        "en": "Interface",
        "fr": "Interface",
    },
    "sidebar.youth": {
        "en": "Youth (Akossiwa)",
        "fr": "Jeune (Akossiwa)",
    },
    "sidebar.policymaker": {
        "en": "Policymaker",
        "fr": "Décideur public",
    },
    "sidebar.operator": {
        "en": "Operator (NGO / Gov)",
        "fr": "Opérateur (ONG / Gouv)",
    },
    "sidebar.language": {
        "en": "UI language",
        "fr": "Langue de l'interface",
    },
    "sidebar.about": {
        "en": "About",
        "fr": "À propos",
    },
    "sidebar.about_body": {
        "en": (
            "**UNMAPPED** maps informal skills to economic opportunity using "
            "real data — ESCO, ILOSTAT, Frey-Osborne.\n\n"
            "- **Module 01** — Skill extraction & ESCO mapping\n"
            "- **Module 02** — Automation risk (Frey-Osborne, LMIC-adjusted)\n"
            "- **Module 03** — Opportunity matching + econometric signals\n\n"
            "Challenge 5 · World Bank Youth Summit\nHack-Nation 5th Global AI Hackathon"
        ),
        "fr": (
            "**UNMAPPED** cartographie les compétences informelles vers les "
            "opportunités économiques avec des données réelles — ESCO, ILOSTAT, Frey-Osborne.\n\n"
            "- **Module 01** — Extraction de compétences & mapping ESCO\n"
            "- **Module 02** — Risque d'automatisation (Frey-Osborne, ajusté LMIC)\n"
            "- **Module 03** — Matching d'opportunités + signaux économétriques\n\n"
            "Challenge 5 · World Bank Youth Summit\nHack-Nation 5th Global AI Hackathon"
        ),
    },

    # ── Youth view header ────────────────────────────────────────
    "youth.persona_section_title": {
        "en": "Quick demo — try a persona",
        "fr": "Démo rapide — essayer un persona",
    },
    "youth.persona_section_caption": {
        "en": (
            "One click loads the persona's text, education level, "
            "languages, and switches the active country."
        ),
        "fr": (
            "Un clic charge le texte du persona, son niveau d'éducation, "
            "ses langues, et change le pays actif."
        ),
    },
    "youth.form_section_title": {
        "en": "Or tell us about yourself",
        "fr": "Ou parlez-nous de vous",
    },
    "youth.form_section_caption": {
        "en": (
            "Describe your experience in any language — French, English, "
            "Fon, Wolof, Bangla. We'll extract your skills and show you "
            "your real economic options."
        ),
        "fr": (
            "Décrivez votre expérience dans n'importe quelle langue — "
            "français, anglais, fon, wolof, bangla. Nous extrayons vos "
            "compétences et vous montrons vos vraies options économiques."
        ),
    },
    "youth.form.text_label": {"en": "Your experience", "fr": "Votre expérience"},
    "youth.form.text_placeholder": {
        "en": "Je répare des téléphones depuis 3 ans…",
        "fr": "Je répare des téléphones depuis 3 ans…",
    },
    "youth.form.text_help": {
        "en": "Write in your own words — any language, any format.",
        "fr": "Écrivez dans vos propres mots — toute langue, tout format.",
    },
    "youth.form.education": {"en": "Education level", "fr": "Niveau d'éducation"},
    "youth.form.languages": {"en": "Languages spoken", "fr": "Langues parlées"},
    "youth.form.name": {"en": "Your name (optional)", "fr": "Votre prénom (optionnel)"},
    "youth.form.submit": {"en": "Generate my profile", "fr": "Générer mon profil"},
    "youth.form.empty_error": {
        "en": "Please describe at least one skill or experience.",
        "fr": "Décrivez au moins une compétence ou expérience.",
    },

    # ── Tabs ─────────────────────────────────────────────────────
    "tabs.profile": {"en": "Profile", "fr": "Profil"},
    "tabs.risk": {"en": "Risk", "fr": "Risque"},
    "tabs.opportunities": {"en": "Opportunities", "fr": "Opportunités"},
    "tabs.mirror": {"en": "Mirror", "fr": "Miroir"},

    # ── Profile tab ──────────────────────────────────────────────
    "profile.title": {"en": "{name}'s Skill Profile", "fr": "Profil de compétences de {name}"},
    "profile.education_lang": {
        "en": "Education: **{level}** (ISCED {isced}) · Languages: {langs}",
        "fr": "Éducation : **{level}** (ISCED {isced}) · Langues : {langs}",
    },
    "profile.no_skills_warn": {
        "en": "No skills were mapped to the ESCO taxonomy. Try a more detailed description.",
        "fr": "Aucune compétence n'a été mappée à la taxonomie ESCO. Essayez une description plus détaillée.",
    },
    "profile.portability": {"en": "Portability", "fr": "Portabilité"},
    "profile.portability_summary": {
        "en": "**{count} ESCO-mapped skills** · {unmapped} unmapped · Standard: {std}",
        "fr": "**{count} compétences mappées ESCO** · {unmapped} non mappées · Norme : {std}",
    },
    "profile.download": {"en": "Download JSON-LD profile", "fr": "Télécharger le profil JSON-LD"},
    "profile.show_qr": {"en": "Show QR code", "fr": "Afficher le QR code"},
    "profile.qr_caption": {
        "en": "Scan to access this profile JSON-LD",
        "fr": "Scanner pour accéder à ce profil JSON-LD",
    },
    "profile.summary_mapped": {
        "en": "skills mapped to ESCO",
        "fr": "compétences mappées ESCO",
    },
    "profile.summary_unmapped": {
        "en": "extracted but unmapped",
        "fr": "extraites mais non mappées",
    },
    "profile.confidence": {
        "en": "Confidence {pct}",
        "fr": "Confiance {pct}",
    },
    "profile.adjacent_label": {
        "en": "Where to evolve (lower automation risk):",
        "fr": "Vers où évoluer (faible risque d'automatisation) :",
    },
    "profile.see_graph": {
        "en": "See interactive skill graph",
        "fr": "Voir le graphe interactif des compétences",
    },
    "profile.graph_legend": {
        "en": (
            "Profile skills (green) · Adjacent ESCO skills (color = category) · "
            "Hover a node for details. Drag to explore."
        ),
        "fr": (
            "Compétences du profil (vert) · Compétences ESCO adjacentes (couleur = catégorie) · "
            "Survolez un nœud pour les détails. Glissez pour explorer."
        ),
    },
    "profile.graph_unavailable": {
        "en": "Skill graph unavailable (PyVis not installed).",
        "fr": "Graphe de compétences indisponible (PyVis non installé).",
    },

    # ── Risk tab ─────────────────────────────────────────────────
    "risk.title": {"en": "Automation Risk Assessment", "fr": "Évaluation du risque d'automatisation"},
    "risk.overall": {"en": "Overall risk", "fr": "Risque global"},
    "risk.avg_prob": {"en": "Avg probability", "fr": "Probabilité moyenne"},
    "risk.pct_at_risk": {"en": "Skills at risk", "fr": "Compétences à risque"},
    "risk.matched_occupations": {
        "en": "Matched Frey-Osborne occupations: ",
        "fr": "Occupations Frey-Osborne correspondantes : ",
    },
    "risk.alternatives_label": {"en": "Lower-risk alternatives:", "fr": "Alternatives à plus faible risque :"},
    "risk.methodology": {"en": "Methodology and limitations", "fr": "Méthodologie et limites"},

    # ── Opportunities tab ────────────────────────────────────────
    "opp.title": {"en": "Matched Opportunities", "fr": "Opportunités appariées"},
    "opp.caption": {
        "en": "Filtered to realistic_for_youth=True · Sorted by profile fit · {country}",
        "fr": "Filtrées sur realistic_for_youth=True · Triées par fit du profil · {country}",
    },
    "opp.empty_warn": {
        "en": "No matching opportunities found. Try a more detailed description.",
        "fr": "Aucune opportunité correspondante. Essayez une description plus détaillée.",
    },
    "opp.details": {"en": "Details — fit score {score}", "fr": "Détails — score de fit {score}"},
    "opp.education_gap": {"en": "Education gap: {gap}", "fr": "Écart d'éducation : {gap}"},
    "opp.skills_to_acquire": {
        "en": "Skills to acquire: {n} ESCO skills not yet in profile",
        "fr": "Compétences à acquérir : {n} compétences ESCO non encore dans le profil",
    },
    "opp.training_resource": {"en": "Training resource", "fr": "Ressource de formation"},

    # ── Mirror tab ───────────────────────────────────────────────
    "mirror.title": {"en": "The Economic Mirror", "fr": "Le Miroir Économique"},
    "mirror.caption": {
        "en": "Real labor market data · ILOSTAT 2024 · Not aspirational — actual market medians",
        "fr": "Données réelles du marché du travail · ILOSTAT 2024 · Pas aspirationnel — vraies médianes du marché",
    },
    "mirror.today": {"en": "Today (informal)", "fr": "Aujourd'hui (informel)"},
    "mirror.best_match": {"en": "Best match for you", "fr": "Meilleure opportunité"},
    "mirror.ict_median": {"en": "ICT sector median", "fr": "Médiane secteur ICT"},
    "mirror.realistic_gap": {"en": "Realistic gap", "fr": "Écart réaliste"},
    "mirror.realistic_meta": {"en": "×{mult} — best accessible opportunity", "fr": "×{mult} — meilleure opportunité accessible"},
    "mirror.aspirational_gap": {"en": "Aspirational gap", "fr": "Écart aspirationnel"},
    "mirror.aspirational_meta": {"en": "×{mult} — ICT sector median", "fr": "×{mult} — médiane secteur ICT"},
    "mirror.next_steps_title": {
        "en": "→ Recommended next steps",
        "fr": "→ Prochaines étapes recommandées",
    },
    "mirror.wages_title": {"en": "Wages by sector ({currency}/month)", "fr": "Salaires par secteur ({currency}/mois)"},
    "mirror.wages_caption": {
        "en": "Signal 1: median wage per sector.",
        "fr": "Signal 1 : salaire médian par secteur.",
    },
    "mirror.jobs_title": {"en": "Where the jobs are", "fr": "Où sont les emplois"},
    "mirror.jobs_caption": {
        "en": "Real employment distribution by sector — ILOSTAT 2024. Signal 2: sector employment share.",
        "fr": "Distribution réelle de l'emploi par secteur — ILOSTAT 2024. Signal 2 : part de l'emploi par secteur.",
    },
    "mirror.transparency_expander": {
        "en": "What this data doesn't show",
        "fr": "Ce que ces données ne montrent pas",
    },

    # ── Policymaker view ─────────────────────────────────────────
    "policy.title": {
        "en": "{country} — Youth Skills Dashboard",
        "fr": "{country} — Tableau de bord des compétences jeunesse",
    },
    "policy.caption": {
        "en": "Aggregate labor market signals · {year} reference · ILOSTAT",
        "fr": "Signaux agrégés du marché du travail · référence {year} · ILOSTAT",
    },
    "policy.youth_unemp": {"en": "Youth unemployment", "fr": "Chômage des jeunes"},
    "policy.youth_neet": {"en": "Youth NEET", "fr": "Jeunes NEET"},
    "policy.informal": {"en": "Informal employment", "fr": "Emploi informel"},
    "policy.population": {"en": "Population 15-24", "fr": "Population 15-24 ans"},
    "policy.wage_section": {
        "en": "Wage Signal — Monthly median by sector",
        "fr": "Signal salarial — Médiane mensuelle par secteur",
    },
    "policy.emp_section": {
        "en": "Employment Signal — Sector share",
        "fr": "Signal emploi — Part par secteur",
    },
    "policy.programs_section": {
        "en": "Recommended Program Areas",
        "fr": "Programmes recommandés",
    },
    "policy.programs_caption": {
        "en": "Data-driven — derived from wage gap and sector signals",
        "fr": "Pilotée par les données — dérivée de l'écart salarial et des signaux sectoriels",
    },
    "policy.methodology": {
        "en": "Methodology and limitations",
        "fr": "Méthodologie et limites",
    },

    # ── Footer ───────────────────────────────────────────────────
    "footer.tagline": {
        "en": "Profile portable across borders · ISCO-08 standardized · ESCO v1.2 mapped · Generated by UNMAPPED · {country}",
        "fr": "Profil portable au-delà des frontières · standardisé ISCO-08 · mappé ESCO v1.2 · Généré par UNMAPPED · {country}",
    },

    # ── Operator console ─────────────────────────────────────────
    "operator.title": {
        "en": "Operator console — onboard a new country",
        "fr": "Console opérateur — ajouter un nouveau pays",
    },
    "operator.subtitle": {
        "en": (
            "Designed for NGO field officers, government agencies, and training "
            "providers. No developer required. ~60 seconds end-to-end."
        ),
        "fr": (
            "Conçu pour les chargés de programme ONG, les agences gouvernementales "
            "et les organismes de formation. Aucun développeur requis. ~60 secondes."
        ),
    },
    "operator.step1_title": {
        "en": "Step 1 — Download the CSV template",
        "fr": "Étape 1 — Télécharger le modèle CSV",
    },
    "operator.step1_caption": {
        "en": (
            "5 columns aligned with ILOSTAT's standard exports. Fill one row per "
            "economic sector (~10–15 rows is typical)."
        ),
        "fr": (
            "5 colonnes alignées sur les exports ILOSTAT standard. Remplissez une "
            "ligne par secteur économique (~10–15 lignes typiquement)."
        ),
    },
    "operator.step1_button": {
        "en": "📥 Download template.csv",
        "fr": "📥 Télécharger template.csv",
    },
    "operator.step2_title": {
        "en": "Step 2 — Upload your CSV + 5 country fields",
        "fr": "Étape 2 — Upload du CSV + 5 champs pays",
    },
    "operator.field.csv": {
        "en": "Filled CSV file *",
        "fr": "Fichier CSV rempli *",
    },
    "operator.field.country_name": {
        "en": "Country name *",
        "fr": "Nom du pays *",
    },
    "operator.field.country_code": {
        "en": "ISO-3 code *",
        "fr": "Code ISO-3 *",
    },
    "operator.field.currency": {
        "en": "Currency (3-letter) *",
        "fr": "Devise (3 lettres) *",
    },
    "operator.field.usd_rate": {
        "en": "Currency per 1 USD *",
        "fr": "Devise par 1 USD *",
    },
    "operator.field.primary_language": {
        "en": "Primary language (ISO 639-1) *",
        "fr": "Langue principale (ISO 639-1) *",
    },
    "operator.field.secondary_languages": {
        "en": "Secondary languages (comma-separated)",
        "fr": "Langues secondaires (séparées par virgule)",
    },
    "operator.advanced": {
        "en": "Advanced — sensible LMIC defaults shown",
        "fr": "Avancé — défauts LMIC raisonnables",
    },
    "operator.field.youth_unemployment_rate": {
        "en": "Youth unemployment rate (%)",
        "fr": "Taux de chômage jeunes (%)",
    },
    "operator.field.informal_employment_share": {
        "en": "Informal employment share (%)",
        "fr": "Part de l'emploi informel (%)",
    },
    "operator.field.youth_neet_rate": {
        "en": "Youth NEET rate (%)",
        "fr": "Taux NEET jeunes (%)",
    },
    "operator.field.lmic_factor": {
        "en": "LMIC automation adjustment factor",
        "fr": "Facteur d'ajustement automatisation LMIC",
    },
    "operator.submit": {
        "en": "🚀 Onboard country",
        "fr": "🚀 Activer le pays",
    },
    "operator.submitting": {
        "en": "Generating config + reloading registry…",
        "fr": "Génération du config + rechargement du registre…",
    },
    "operator.success_title": {
        "en": "✅ {country_name} ({country_code}) is LIVE",
        "fr": "✅ {country_name} ({country_code}) est EN LIGNE",
    },
    "operator.success_hint": {
        "en": (
            "Switch to **{country_code}** in the sidebar dropdown to see the "
            "new country in the Youth and Policymaker views. Add opportunities "
            "via `POST /api/opportunities/{country_code}/bulk` (see INTEGRATION.md)."
        ),
        "fr": (
            "Sélectionnez **{country_code}** dans le menu déroulant à gauche "
            "pour voir le nouveau pays dans les vues Jeune et Décideur. Ajoutez "
            "des opportunités via `POST /api/opportunities/{country_code}/bulk` "
            "(voir INTEGRATION.md)."
        ),
    },
    "operator.csv_required": {
        "en": "Upload a CSV file before submitting.",
        "fr": "Veuillez uploader un fichier CSV avant de soumettre.",
    },

    # ── API errors ───────────────────────────────────────────────
    "error.api_unreachable": {
        "en": "UNMAPPED API not reachable at `{url}`. Start the API with `make api` in another terminal.",
        "fr": "API UNMAPPED inaccessible à `{url}`. Démarrez l'API avec `make api` dans un autre terminal.",
    },
}


def get_lang() -> str:
    """Return the active UI language code (default: en)."""
    return st.session_state.get("ui_lang", DEFAULT_LANG)


def t(key: str, **kwargs) -> str:
    """Translate a key into the active language, with optional .format() kwargs.

    Falls back to English, then to the key itself if missing.
    """
    lang = get_lang()
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
