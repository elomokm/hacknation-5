"""Country config loader — stub for Phase 0, fully implemented in Phase 2."""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent / "configs"

_CODE_TO_FILE: dict[str, str] = {
    "BEN": "benin",
    "SEN": "senegal",
}


def load_config(country_code: str) -> dict:
    """Load and return the YAML config for a given 3-letter country code."""
    filename = _CODE_TO_FILE.get(country_code.upper())
    if filename is None:
        raise ValueError(f"Unknown country code: {country_code!r}. Known: {list(_CODE_TO_FILE)}")
    path = _CONFIG_DIR / f"{filename}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info("Loaded config for %s from %s", country_code, path)
    return config


def get_active_config() -> dict:
    """Load config based on ACTIVE_COUNTRY env var (default: BEN)."""
    country_code = os.getenv("ACTIVE_COUNTRY", "BEN").upper()
    return load_config(country_code)
