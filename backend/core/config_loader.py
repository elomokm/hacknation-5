"""Country config loader — auto-discovers YAMLs in backend/configs/.

No hardcoded country list. Drop a `<code>.yaml` in configs/ → call reload() →
the country becomes available across the API and frontend with zero code changes.
"""

import logging
import os
from pathlib import Path

import yaml

from core.models import CountryConfig

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent
_CONFIG_DIR = _BACKEND_DIR / "configs"


def _discover_configs() -> dict[str, str]:
    """Scan configs/*.yaml, read country_code from each, build code → filename map."""
    out: dict[str, str] = {}
    if not _CONFIG_DIR.exists():
        logger.warning("Config dir does not exist: %s", _CONFIG_DIR)
        return out
    for yml in sorted(_CONFIG_DIR.glob("*.yaml")):
        try:
            with open(yml, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.warning("Skipping malformed YAML %s: %s", yml.name, e)
            continue
        code = str(raw.get("country_code", "")).upper().strip()
        if not code:
            logger.warning("Skipping %s — no country_code field", yml.name)
            continue
        if code in out:
            logger.warning(
                "Duplicate country_code %r in %s (already from %s.yaml) — ignored",
                code, yml.name, out[code],
            )
            continue
        out[code] = yml.stem
    logger.info("Discovered %d country configs: %s", len(out), sorted(out.keys()))
    return out


# Module-level cache, refreshable via reload_configs().
_CODE_TO_FILE: dict[str, str] = _discover_configs()


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
            f"Supported: {sorted(_CODE_TO_FILE.keys())}. "
            f"Drop {code.lower()}.yaml in backend/configs/ and call /api/config/reload."
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
    """Return all auto-discovered country codes."""
    return sorted(_CODE_TO_FILE.keys())


def reload_configs() -> list[str]:
    """Re-scan backend/configs/ and refresh the country registry.

    Returns the new list of available country codes. Useful after dropping
    a new YAML file at runtime — exposed via POST /api/config/reload.
    """
    global _CODE_TO_FILE
    _CODE_TO_FILE = _discover_configs()
    return sorted(_CODE_TO_FILE.keys())


def register_country(code: str, yaml_filename: str) -> None:
    """Backwards-compat shim — prefer dropping a YAML and calling reload_configs()."""
    _CODE_TO_FILE[code.upper()] = yaml_filename
    logger.info("Registered country (manual): %s → %s.yaml", code.upper(), yaml_filename)


def _validate_referenced_files(config: CountryConfig) -> None:
    """Raise FileNotFoundError if any data file referenced in the config is missing."""
    refs = [
        config.labor_data.source_file,
        config.projections.source_file,
        config.opportunities.source_file,
    ]
    for ref in refs:
        full_path = _BACKEND_DIR / ref
        if not full_path.exists():
            raise FileNotFoundError(
                f"Config for {config.country_code} references missing file: {full_path}\n"
                f"  (declared as: {ref!r})"
            )
    logger.debug(
        "All referenced files verified for %s: %s", config.country_code, refs
    )
