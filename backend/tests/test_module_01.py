"""Module 01 integration test — 3 real scenarios with live API calls."""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load API key from backend/.env before any module import
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from core.config_loader import load_config
from core.models import StandardizedProfile
from module_01_skills.extractor import extract_skills
from module_01_skills.profile_generator import generate_profile
from module_01_skills.taxonomy_mapper import TaxonomyMapper

mapper = TaxonomyMapper()

_DIVIDER = "=" * 65


def run_scenario(
    label: str,
    text: str,
    user_id: str,
    user_name: str,
    education_level: str,
    languages: list[str],
    country_code: str,
    min_extracted: int,
    min_mapped: int,
) -> StandardizedProfile:
    """Run one scenario end-to-end and print results."""
    logger.info("")
    logger.info(_DIVIDER)
    logger.info("SCENARIO %s", label)
    logger.info(_DIVIDER)
    logger.info("Input: %r", text[:120] + ("..." if len(text) > 120 else ""))

    config = load_config(country_code)

    # Step 1 — extract
    extracted = extract_skills(text)
    logger.info("Extracted: %d skills", len(extracted))
    for s in extracted:
        logger.info(
            "  [%.2f] %-35s | cat=%-20s | evidence=%r",
            s.confidence, s.normalized_label, s.category, s.evidence[:50],
        )

    # Step 2 — map
    mapped = mapper.map_skills_batch(extracted)
    unmapped = [e for e in extracted if not any(m.raw_extraction == e for m in mapped)]
    logger.info(
        "Mapped: %d / %d  (unmapped: %d)",
        len(mapped), len(extracted), len(unmapped),
    )
    for m in mapped:
        logger.info(
            "  %s → %s %-35s | ISCO=%s | conf=%.2f",
            m.raw_extraction.normalized_label[:25].ljust(25),
            m.esco_id,
            m.esco_label[:30],
            ",".join(m.isco_groups),
            m.match_confidence,
        )
    if unmapped:
        logger.info("  Unmapped (no ESCO match above threshold):")
        for u in unmapped:
            logger.info("    – %s", u.normalized_label)

    # Step 3 — profile
    profile = generate_profile(
        user_id=user_id,
        user_name=user_name,
        education_level=education_level,
        languages=languages,
        extracted_skills=extracted,
        mapped_skills=mapped,
        config=config,
    )

    logger.info("")
    logger.info("Summary:")
    logger.info("  %s", profile.human_readable_summary)
    logger.info("")
    logger.info("Full profile JSON:")
    profile_json = profile.model_dump(mode="json", by_alias=True)
    logger.info("%s", json.dumps(profile_json, indent=2, ensure_ascii=False))

    # Assertions
    assert len(extracted) >= min_extracted, (
        f"{label}: expected ≥{min_extracted} extracted skills, got {len(extracted)}"
    )
    assert len(mapped) >= min_mapped, (
        f"{label}: expected ≥{min_mapped} mapped skills, got {len(mapped)}"
    )
    assert profile.country_code == country_code
    assert profile.name == user_name
    assert isinstance(profile.human_readable_summary, str)
    assert len(profile.human_readable_summary) > 20
    assert "@context" in profile_json
    assert "@type" in profile_json
    assert profile_json["portability"]["format_version"] == "1.0"

    logger.info("✓ Scenario %s — PASSED", label)
    return profile


# ──────────────────────────────────────────────────────────────────
# SCENARIO A — Akossiwa (Bénin, French, formal + informal skills)
# ──────────────────────────────────────────────────────────────────
SCENARIO_A_TEXT = (
    "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
    "depuis 4 ans dans mon atelier à Cotonou. J'ai appris HTML et un "
    "peu de Python sur YouTube. J'aide ma cousine à gérer son magasin "
    "de tissus, je tiens son inventaire sur Excel."
)

# ──────────────────────────────────────────────────────────────────
# SCENARIO B — Mamadou (Sénégal, French/Wolof, agricultural focus)
# ──────────────────────────────────────────────────────────────────
SCENARIO_B_TEXT = (
    "Mamadou, BFEM. Je travaille avec mon père sur une ferme près de "
    "Thiès depuis 6 ans. On cultive du mil et des arachides. Je conduis "
    "le tracteur. Je vends au marché chaque semaine."
)

# ──────────────────────────────────────────────────────────────────
# SCENARIO C — Edge case: sparse input
# ──────────────────────────────────────────────────────────────────
SCENARIO_C_TEXT = "I want a job."


if __name__ == "__main__":
    profile_a = run_scenario(
        label="A — Akossiwa (Bénin)",
        text=SCENARIO_A_TEXT,
        user_id="usr_akossiwa_001",
        user_name="Akossiwa",
        education_level="BEPC",
        languages=["fr", "fon"],
        country_code="BEN",
        min_extracted=5,
        min_mapped=3,  # Python has no explicit ESCO label; honest limit
    )

    profile_b = run_scenario(
        label="B — Mamadou (Sénégal)",
        text=SCENARIO_B_TEXT,
        user_id="usr_mamadou_001",
        user_name="Mamadou",
        education_level="BFEM",
        languages=["fr", "wo"],
        country_code="SEN",
        min_extracted=4,
        min_mapped=2,
    )

    # Scenario C: edge case — no skills
    logger.info("")
    logger.info(_DIVIDER)
    logger.info("SCENARIO C — Edge case: sparse input")
    logger.info(_DIVIDER)
    config_c = load_config("BEN")
    extracted_c = extract_skills(SCENARIO_C_TEXT)
    mapped_c = mapper.map_skills_batch(extracted_c)
    profile_c = generate_profile(
        user_id="usr_edge_001",
        user_name="Anonymous",
        education_level="aucun",
        languages=["en"],
        extracted_skills=extracted_c,
        mapped_skills=mapped_c,
        config=config_c,
    )
    logger.info("Extracted: %d (expected 0 or 1)", len(extracted_c))
    logger.info("Mapped   : %d", len(mapped_c))
    logger.info("Summary  : %s", profile_c.human_readable_summary)

    assert len(extracted_c) <= 1, f"Edge case: expected ≤1 extracted, got {len(extracted_c)}"
    assert len(profile_c.human_readable_summary) > 20
    logger.info("✓ Scenario C — PASSED")

    logger.info("")
    logger.info(_DIVIDER)
    logger.info("ALL SCENARIOS PASSED — Module 01 ready")
    logger.info(_DIVIDER)
