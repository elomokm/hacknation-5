"""Configuration endpoints — surface the localizability layer."""

from fastapi import APIRouter, HTTPException

from api.dependencies import get_country_config
from core.config_loader import list_available_countries, load_config, reload_configs
from core.models import CountryConfig

router = APIRouter()


@router.post(
    "/reload",
    summary="Re-scan backend/configs/ for new country YAMLs",
    description=(
        "Triggers an auto-discovery pass over the configs directory. "
        "Use this after dropping a new <code>.yaml file in production "
        "to make it available without restarting the API. Also clears "
        "per-country singleton caches (matchers, econometric loaders)."
    ),
)
async def reload() -> dict:
    """Re-scan configs/ and clear per-country singletons."""
    countries = reload_configs()
    # Clear per-country instance caches so newly-added/changed configs
    # are picked up on the next request.
    from api.dependencies import _ECONS, _MATCHERS
    _MATCHERS.clear()
    _ECONS.clear()
    return {
        "countries": countries,
        "count": len(countries),
        "note": "Per-country singletons cleared. Next request will reload from YAML.",
    }


@router.get(
    "/countries",
    summary="List supported countries",
    description=(
        "Returns metadata for every configured country. "
        "Adding a new country = one YAML file. No code changes."
    ),
)
async def list_countries() -> list[dict]:
    """List all supported countries with summary metadata."""
    out: list[dict] = []
    for code in list_available_countries():
        try:
            config = load_config(code)
        except Exception:  # noqa: BLE001 — skip malformed configs
            continue
        out.append({
            "code": code,
            "name": config.country,
            "primary_language": config.ui.primary_language,
            "supported_languages": config.ui.supported_languages,
            "currency": config.labor_data.currency,
            "lmic_adjustment_factor": config.automation_calibration.lmic_adjustment_factor,
            "education_levels": config.education_taxonomy.levels,
            "opportunity_types": config.opportunities.types_enabled,
        })
    return out


@router.get(
    "/schema",
    summary="CountryConfig JSON schema",
    description=(
        "Returns the JSON schema for CountryConfig. "
        "This is the contract for adding a new country."
    ),
)
async def get_schema() -> dict:
    """Return the JSON schema documentation for adding a new country."""
    return {
        "schema": CountryConfig.model_json_schema(),
        "how_to_add_country": [
            "1. Create backend/data/ilostat/{code_lower}_labor_2024.json",
            "2. Create backend/configs/{code_lower}.yaml using this schema",
            "3. Register the country in backend/core/config_loader.py _CODE_TO_FILE",
            "4. (Optional) Create backend/data/opportunities/{code_lower}_opportunities.json",
            "See LOCALIZATION.md for the full guide.",
        ],
    }


@router.get(
    "/{country_code}",
    response_model=CountryConfig,
    summary="Full country configuration",
    description="Returns the complete CountryConfig for a 3-letter country code.",
)
async def get_country_config_endpoint(country_code: str) -> CountryConfig:
    """Return the full CountryConfig for a country."""
    return get_country_config(country_code)
