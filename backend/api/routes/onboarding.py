"""No-code country onboarding endpoint.

The operator-facing entry point for the "infrastructure" claim. An NGO field
officer uploads an ILOSTAT-aligned 5-column CSV and fills 5 metadata fields;
the system generates the country YAML + labor JSON + empty opportunities file,
hot-reloads the config registry, and the country is live in the API and the
Streamlit dropdown — no developer, no deploy.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from core.config_loader import reload_configs
from core.csv_to_country import CountryMetadata, build_country_files
from core.models import CountryConfig

logger = logging.getLogger(__name__)
router = APIRouter()

_BACKEND_DIR = Path(__file__).parent.parent.parent
_CONFIG_DIR = _BACKEND_DIR / "configs"
_ILOSTAT_DIR = _BACKEND_DIR / "data" / "ilostat"
_OPP_DIR = _BACKEND_DIR / "data" / "opportunities"
_TEMPLATE_PATH = _BACKEND_DIR / "data" / "templates" / "ilostat_country_template.csv"


class OnboardingResponse(BaseModel):
    country_code: str
    country_name: str
    sectors_imported: int
    growth_strategic_sectors: list[str]
    was_replacement: bool
    available_countries: list[str]
    note: str


def _atomic_write_text(path: Path, content: str) -> None:
    """Write text to disk via tmp + rename — same pattern as opportunity.py."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _split_secondary_langs(raw: str) -> list[str]:
    """Parse comma-separated language codes from a form field."""
    if not raw:
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


@router.get(
    "/template.csv",
    summary="Download the 5-column ILOSTAT-aligned CSV template",
    description=(
        "Returns the canonical CSV the operator console expects. Comments "
        "(`#`-prefixed lines) at the top explain each column. Sample rows "
        "are included so the file is uploadable as-is for a smoke test."
    ),
    response_class=FileResponse,
)
async def download_template() -> FileResponse:
    """Serve the bundled CSV template."""
    if not _TEMPLATE_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Template missing at {_TEMPLATE_PATH} (deployment bug).",
        )
    return FileResponse(
        _TEMPLATE_PATH,
        media_type="text/csv",
        filename="ilostat_country_template.csv",
    )


@router.post(
    "/country",
    response_model=OnboardingResponse,
    summary="Onboard a new country from a CSV upload (no developer required)",
    description=(
        "Multipart endpoint: a CSV file (5 columns, see /template.csv) plus 5 "
        "required form fields (country_name, country_code, currency, usd_rate, "
        "primary_language). Generates the YAML config, ILOSTAT-shaped labor JSON, "
        "and an empty opportunities file; validates the generated config against "
        "the CountryConfig schema; hot-reloads the registry. The new country is "
        "available immediately at /api/config/{code} and in the Streamlit sidebar."
    ),
)
async def onboard_country(
    csv: UploadFile = File(..., description="5-column CSV — see /template.csv"),
    country_name: str = Form(..., description="Display name, e.g. 'Côte d'Ivoire'"),
    country_code: str = Form(..., description="ISO-3, e.g. 'CIV'"),
    currency: str = Form(..., description="3-letter ISO 4217, e.g. 'XOF'"),
    usd_rate: float = Form(..., description="Local currency per 1 USD, e.g. 600"),
    primary_language: str = Form(..., description="ISO 639-1, e.g. 'fr'"),
    secondary_languages: str = Form(
        "",
        description="Comma-separated ISO 639-1 codes, e.g. 'en,wo'",
    ),
    youth_unemployment_rate: float = Form(12.0),
    informal_employment_share: float = Form(75.0),
    youth_neet_rate: float = Form(25.0),
    lmic_adjustment_factor: float = Form(0.65),
) -> OnboardingResponse:
    """Generate config + data files from the upload and reload the registry."""
    # ── 1. Validate metadata via Pydantic ───────────────────────────────
    try:
        metadata = CountryMetadata(
            country_name=country_name,
            country_code=country_code,
            currency=currency,
            usd_rate=usd_rate,
            primary_language=primary_language,
            secondary_languages=_split_secondary_langs(secondary_languages),
            youth_unemployment_rate=youth_unemployment_rate,
            informal_employment_share=informal_employment_share,
            youth_neet_rate=youth_neet_rate,
            lmic_adjustment_factor=lmic_adjustment_factor,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata: {e.errors()}")

    # ── 2. Read + parse the CSV ─────────────────────────────────────────
    try:
        csv_bytes = await csv.read()
        csv_text = csv_bytes.decode("utf-8-sig")  # tolerate UTF-8 BOM
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV is not UTF-8 encoded. Re-save as UTF-8 and retry.",
        )

    try:
        files = build_country_files(csv_text=csv_text, metadata=metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

    # ── 3. Validate the generated YAML against CountryConfig schema ─────
    # Catches malformed defaults early so we never write a YAML that the
    # config_loader would reject on the next reload.
    try:
        CountryConfig(**files.yaml_dict)
    except ValidationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generated config failed schema validation: {e.errors()}",
        )

    # ── 4. Compute target paths + write atomically ──────────────────────
    code_lower = metadata.country_code.lower()
    code_upper = metadata.country_code.upper()
    yaml_path = _CONFIG_DIR / f"{code_lower}.yaml"
    labor_path = _ILOSTAT_DIR / f"{code_lower}_labor_2024.json"
    opp_path = _OPP_DIR / f"{code_lower}_opportunities.json"

    was_replacement = yaml_path.exists()

    _atomic_write_text(
        labor_path,
        json.dumps(files.labor_json, indent=2, ensure_ascii=False),
    )
    _atomic_write_text(
        opp_path,
        json.dumps(files.opportunities_json, indent=2, ensure_ascii=False),
    )
    _atomic_write_text(
        yaml_path,
        yaml.safe_dump(files.yaml_dict, sort_keys=False, allow_unicode=True),
    )

    # ── 5. Reload the registry + clear per-country caches ───────────────
    countries = reload_configs()
    from api.dependencies import _ECONS, _MATCHERS
    _MATCHERS.pop(code_upper, None)
    _ECONS.pop(code_upper, None)

    logger.info(
        "Onboarded country %s (%s) — %d sectors, replacement=%s",
        code_upper, metadata.country_name, len(files.labor_json["wage_by_sector"]),
        was_replacement,
    )

    return OnboardingResponse(
        country_code=code_upper,
        country_name=metadata.country_name,
        sectors_imported=len(files.labor_json["wage_by_sector"]),
        growth_strategic_sectors=files.yaml_dict["labor_data"]["growth_strategic_sectors"],
        was_replacement=was_replacement,
        available_countries=countries,
        note=(
            f"Country live at /api/config/{code_upper}. "
            "Add opportunities via POST /api/opportunities/{code}/bulk."
        ),
    )
