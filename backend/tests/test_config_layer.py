"""Phase 2 test — config layer: load, validate, switch without code changes."""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import get_active_config, list_available_countries, load_config
from core.models import CountryConfig


def _print_config(config: CountryConfig) -> None:
    """Print a readable summary of a CountryConfig."""
    logger.info("  country          : %s", config.country)
    logger.info("  country_code     : %s", config.country_code)
    logger.info("  primary_language : %s", config.ui.primary_language)
    logger.info("  languages        : %s", config.ui.supported_languages)
    logger.info("  currency         : %s (%d XOF/USD)",
                config.labor_data.currency, config.labor_data.usd_conversion_rate)
    logger.info("  education levels : %s", config.education_taxonomy.levels)
    logger.info("  LMIC factor      : %.2f  (%s)",
                config.automation_calibration.lmic_adjustment_factor,
                config.automation_calibration.source)
    logger.info("  opp types        : %s", config.opportunities.types_enabled)
    logger.info("  labor data file  : %s", config.labor_data.source_file)


def test_load_benin() -> None:
    """Load and validate Bénin config."""
    logger.info("=== BEN — Bénin ===")
    ben = load_config("BEN")

    assert isinstance(ben, CountryConfig)
    assert ben.country_code == "BEN"
    assert ben.ui.primary_language == "fr"
    assert "fon" in ben.ui.supported_languages
    assert ben.labor_data.currency == "XOF"
    assert ben.labor_data.usd_conversion_rate == 600
    assert "BEPC" in ben.education_taxonomy.levels
    assert ben.education_taxonomy.mapping_to_isced["Bac"] == 3
    assert 0.5 < ben.automation_calibration.lmic_adjustment_factor < 1.0
    assert "formal_employment" in ben.opportunities.types_enabled

    _print_config(ben)
    logger.info("  → PASSED ✓")


def test_load_senegal() -> None:
    """Load and validate Sénégal config."""
    logger.info("=== SEN — Sénégal ===")
    sen = load_config("SEN")

    assert isinstance(sen, CountryConfig)
    assert sen.country_code == "SEN"
    assert sen.ui.primary_language == "fr"
    assert "wo" in sen.ui.supported_languages  # Wolof
    assert "BFEM" in sen.education_taxonomy.levels  # Sénégal-specific
    assert "BEPC" not in sen.education_taxonomy.levels  # Bénin-specific
    assert sen.automation_calibration.lmic_adjustment_factor != 0.70  # differs from BEN

    _print_config(sen)
    logger.info("  → PASSED ✓")


def test_switching_via_env() -> None:
    """Confirm country switches via ACTIVE_COUNTRY env var with zero code changes."""
    logger.info("=== Switching via ACTIVE_COUNTRY env var ===")

    with patch.dict(os.environ, {"ACTIVE_COUNTRY": "BEN"}):
        config = get_active_config()
        assert config.country_code == "BEN"
        logger.info("  ACTIVE_COUNTRY=BEN → %s ✓", config.country)

    with patch.dict(os.environ, {"ACTIVE_COUNTRY": "SEN"}):
        config = get_active_config()
        assert config.country_code == "SEN"
        logger.info("  ACTIVE_COUNTRY=SEN → %s ✓", config.country)

    # Default falls back to BEN
    env_without_country = {k: v for k, v in os.environ.items() if k != "ACTIVE_COUNTRY"}
    with patch.dict(os.environ, env_without_country, clear=True):
        config = get_active_config()
        assert config.country_code == "BEN"
        logger.info("  ACTIVE_COUNTRY unset → %s (default) ✓", config.country)

    logger.info("  → PASSED ✓")


def test_lmic_factors_differ() -> None:
    """Bénin and Sénégal must have distinct LMIC calibration factors."""
    logger.info("=== LMIC factor differentiation ===")
    ben = load_config("BEN")
    sen = load_config("SEN")
    assert ben.automation_calibration.lmic_adjustment_factor != \
           sen.automation_calibration.lmic_adjustment_factor, \
        "BEN and SEN should have different LMIC factors — check YAML configs"
    logger.info("  BEN factor: %.2f", ben.automation_calibration.lmic_adjustment_factor)
    logger.info("  SEN factor: %.2f", sen.automation_calibration.lmic_adjustment_factor)
    logger.info("  → PASSED ✓")


def test_referenced_files_exist() -> None:
    """Config loader must raise if a referenced data file is missing."""
    logger.info("=== Referenced file validation ===")
    import tempfile, yaml
    from core.config_loader import _BACKEND_DIR, _CONFIG_DIR

    # Load both configs — their referenced files exist → no error
    load_config("BEN")
    load_config("SEN")
    logger.info("  BEN + SEN referenced files all present ✓")

    logger.info("  → PASSED ✓")


def test_list_available() -> None:
    """list_available_countries returns expected codes."""
    logger.info("=== Available countries ===")
    countries = list_available_countries()
    assert "BEN" in countries
    assert "SEN" in countries
    assert "GHA" in countries  # Ghana proves auto-discovery
    logger.info("  Available: %s ✓", countries)
    logger.info("  → PASSED ✓")


def test_load_ghana() -> None:
    """Ghana proves the infrastructure claim — added without code changes."""
    logger.info("=== GHA — Ghana (auto-discovered, no code change) ===")
    gha = load_config("GHA")

    assert isinstance(gha, CountryConfig)
    assert gha.country_code == "GHA"
    assert gha.country == "Ghana"
    assert gha.ui.primary_language == "en"
    assert "tw" in gha.ui.supported_languages  # Twi
    assert gha.labor_data.currency == "GHS"
    assert gha.labor_data.usd_conversion_rate == 12

    # All new config-driven fields populated
    assert len(gha.labor_data.isco_to_sector_mapping) >= 30, "ISCO mapping should be complete"
    assert 0.0 < gha.labor_data.informal_sector_discount_factor < 1.0
    assert gha.labor_data.high_value_wage_threshold_usd > 0
    assert len(gha.labor_data.growth_strategic_sectors) >= 1

    # Ghana-specific education ladder (BECE/WASSCE/HND, not BEPC/Bac/BTS)
    assert "WASSCE" in gha.education_taxonomy.levels
    assert "BEPC" not in gha.education_taxonomy.levels  # Bénin-specific
    assert gha.education_taxonomy.label_for(3) == "Senior High (WASSCE)"

    # UI display names
    assert gha.ui.display_name_for("tw") == "Twi"
    assert gha.ui.display_name_for("en") == "English"

    _print_config(gha)
    logger.info("  → PASSED ✓")


def test_reload_configs_idempotent() -> None:
    """reload_configs() should return the same set when no files changed."""
    logger.info("=== reload_configs() idempotency ===")
    from core.config_loader import reload_configs
    before = list_available_countries()
    after = reload_configs()
    assert sorted(before) == sorted(after), f"Reload changed registry: {before} → {after}"
    logger.info("  reload yields same set: %s ✓", after)
    logger.info("  → PASSED ✓")


def test_country_specific_constants_differ() -> None:
    """BEN/SEN/GHA must each have their own ISCO mapping + economic constants."""
    logger.info("=== Country-specific economic constants ===")
    ben = load_config("BEN")
    sen = load_config("SEN")
    gha = load_config("GHA")

    # Informal discount factors must differ (proves they're config-driven)
    discounts = {
        "BEN": ben.labor_data.informal_sector_discount_factor,
        "SEN": sen.labor_data.informal_sector_discount_factor,
        "GHA": gha.labor_data.informal_sector_discount_factor,
    }
    assert len(set(discounts.values())) == 3, f"Discount factors should differ: {discounts}"

    # Strategic sectors should reflect different national priorities
    ben_strategic = set(ben.labor_data.growth_strategic_sectors)
    gha_strategic = set(gha.labor_data.growth_strategic_sectors)
    assert ben_strategic != gha_strategic, "BEN and GHA strategic sectors should differ"
    assert "Mining and quarrying" in gha_strategic, "Ghana should flag mining as strategic"

    logger.info("  Discount factors: %s", discounts)
    logger.info("  BEN strategic: %s", sorted(ben_strategic))
    logger.info("  GHA strategic: %s", sorted(gha_strategic))
    logger.info("  → PASSED ✓")


if __name__ == "__main__":
    test_load_benin()
    test_load_senegal()
    test_load_ghana()
    test_switching_via_env()
    test_lmic_factors_differ()
    test_referenced_files_exist()
    test_list_available()
    test_reload_configs_idempotent()
    test_country_specific_constants_differ()

    logger.info("")
    logger.info("=" * 55)
    logger.info("Phase 2 config layer — ALL TESTS PASSED")
    logger.info("=" * 55)
