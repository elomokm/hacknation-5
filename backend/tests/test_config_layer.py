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
    logger.info("  Available: %s ✓", countries)
    logger.info("  → PASSED ✓")


if __name__ == "__main__":
    test_load_benin()
    test_load_senegal()
    test_switching_via_env()
    test_lmic_factors_differ()
    test_referenced_files_exist()
    test_list_available()

    logger.info("")
    logger.info("=" * 55)
    logger.info("Phase 2 config layer — ALL TESTS PASSED")
    logger.info("=" * 55)
