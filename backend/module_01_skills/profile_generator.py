"""Module 01 — Profile generator: assembles StandardizedProfile from mapped skills.

One LLM call (human_readable_summary). Everything else is deterministic.
"""

import logging
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

from core.models import CountryConfig, ExtractedSkill, MappedSkill, StandardizedProfile

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5"

_ISCED_LABELS: dict[int, str] = {
    0: "No formal education",
    1: "Primary education",
    2: "Lower secondary education",
    3: "Upper secondary education",
    4: "Post-secondary non-tertiary",
    5: "Short-cycle tertiary (BTS/DUT)",
    6: "Bachelor's or equivalent",
    7: "Master's or equivalent",
    8: "Doctoral or equivalent",
}

_LANG_DISPLAY: dict[str, str] = {
    "fr": "French",
    "en": "English",
    "wo": "Wolof",
    "fon": "Fon",
    "ha": "Hausa",
}


def _client() -> anthropic.Anthropic:
    """Return a fresh Anthropic client."""
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _resolve_education(level: str, config: CountryConfig) -> dict:
    """Build education dict with ISCED mapping from country config."""
    isced_code = config.education_taxonomy.mapping_to_isced.get(level)
    return {
        "level": level,
        "isced": isced_code,
        "isced_label": _ISCED_LABELS.get(isced_code, "Unknown") if isced_code is not None else "Unknown",
        "country_taxonomy": config.country_code,
    }


def _build_portability(mapped: list[MappedSkill], unmapped_count: int) -> dict:
    """Assemble the portability block."""
    isco_codes = sorted({code for skill in mapped for code in skill.isco_groups})
    return {
        "isco_codes": isco_codes,
        "esco_count": len(mapped),
        "unmapped_skill_count": unmapped_count,
        "format_version": "1.0",
        "standard": "ESCO v1.2 / ISCO-08",
    }


def _generate_summary(
    name: str,
    education_label: str,
    mapped: list[MappedSkill],
    language: str,
    config: CountryConfig,
) -> str:
    """Call the LLM once to produce a 1-paragraph human-readable summary."""
    lang_name = _LANG_DISPLAY.get(language, "French")

    if mapped:
        skill_labels = ", ".join(s.esco_label for s in mapped[:8])
        skills_block = f"Skills identified: {skill_labels}"
    else:
        skills_block = "No specific skills were identified from the provided description."

    prompt = (
        f"Write a 1-paragraph professional summary (maximum 150 words) for {name}.\n\n"
        f"Education: {education_label}\n"
        f"{skills_block}\n"
        f"Country context: {config.country}\n\n"
        f"Style: Clear, respectful, grounded in economic reality. "
        f"Focus on concrete skills and potential pathways. Not preachy.\n"
        f"If no skills were found, honestly state that more information is needed "
        f"to build a complete profile.\n\n"
        f"Write ONLY the paragraph in {lang_name}. No preamble, no title."
    )

    try:
        response = _client().messages.create(
            model=_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Summary generation failed: %s", exc)
        return (
            "Profil en cours de construction. "
            "Partagez plus de détails sur votre expérience pour enrichir ce résumé."
        )


def generate_profile(
    user_id: str,
    user_name: str,
    education_level: str,
    languages: list[str],
    extracted_skills: list[ExtractedSkill],
    mapped_skills: list[MappedSkill],
    config: CountryConfig,
) -> StandardizedProfile:
    """Assemble a StandardizedProfile from extraction + mapping outputs.

    Makes one LLM call (human_readable_summary). All other fields are deterministic.
    """
    profile_id = user_id or str(uuid.uuid4())
    language = languages[0] if languages else config.ui.primary_language

    education = _resolve_education(education_level, config)
    skill_categories = dict(Counter(s.esco_category for s in mapped_skills))
    portability = _build_portability(
        mapped_skills, len(extracted_skills) - len(mapped_skills)
    )

    summary = _generate_summary(
        name=user_name,
        education_label=education.get("isced_label", education_level),
        mapped=mapped_skills,
        language=language,
        config=config,
    )

    profile = StandardizedProfile(
        profile_id=profile_id,
        generated_at=datetime.now(timezone.utc),
        country_code=config.country_code,
        name=user_name,
        education=education,
        languages=languages,
        skills=mapped_skills,
        skill_categories=skill_categories,
        portability=portability,
        human_readable_summary=summary,
    )

    logger.info(
        "Profile generated: %s | %d skills | country=%s",
        profile_id,
        len(mapped_skills),
        config.country_code,
    )
    return profile
