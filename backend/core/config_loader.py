"""Country config loader — resolves YAML to a validated CountryConfig."""

import logging
import os
from pathlib import Path

import yaml

from core.models import CountryConfig

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent
_CONFIG_DIR = _BACKEND_DIR / "configs"

# Maps 3-letter ISO country code → YAML filename (without extension)
_CODE_TO_FILE: dict[str, str] = {
    "BEN": "benin",
    "SEN": "senegal",
}


def load_config(country_code: str) -> CountryConfig:
    """Load, validate, and return a CountryConfig for the given 3-letter country code.

    Raises ValueError for unknown codes, FileNotFoundError for missing files.
    Also validates that every data file referenced in the config actually exists.
    """
    code = country_code.upper().strip()
    filename = _CODE_TO_FILE.get(code)
    if filename is None:
        raise ValueError(
            f"Unknown country code: {code!r}. "
            f"Supported: {sorted(_CODE_TO_FILE.keys())}"
        )

    yaml_path = _CONFIG_DIR / f"{filename}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = CountryConfig(**raw)
    _validate_referenced_files(config)

    logger.info("Config loaded: %s (%s)", config.country, config.country_code)
    return config


def get_active_config() -> CountryConfig:
    """Load config for the country set in ACTIVE_COUNTRY env var (default: BEN)."""
    code = os.getenv("ACTIVE_COUNTRY", "BEN").upper().strip()
    return load_config(code)


def list_available_countries() -> list[str]:
    """Return all registered country codes."""
    return sorted(_CODE_TO_FILE.keys())


def register_country(code: str, yaml_filename: str) -> None:
    """Register a new country code → YAML filename mapping at runtime."""
    _CODE_TO_FILE[code.upper()] = yaml_filename
    logger.info("Registered country: %s → %s.yaml", code.upper(), yaml_filename)


def _validate_referenced_files(config: CountryConfig) -> None:
    """Raise FileNotFoundError if any data file referenced in the config is missing."""
    refs = [
        config.labor_data.source_file,
        config.projections.source_file,
    ]
    for ref in refs:
        # source_file is relative to backend/ (e.g. "data/ilostat/benin_labor_2024.json")
        full_path = _BACKEND_DIR / ref
        if not full_path.exists():
            raise FileNotFoundError(
                f"Config for {config.country_code} references missing file: {full_path}\n"
                f"  (declared as: {ref!r})"
            )
    logger.debug(
        "All referenced files verified for %s: %s", config.country_code, refs
    )
