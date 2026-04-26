"""CSV → country files generator.

Pure logic: takes a 5-column ILOSTAT-aligned CSV plus operator metadata and
returns the three dicts needed to register a new country (YAML config, labor
JSON, empty opportunities JSON). No file I/O, no FastAPI deps — testable
in isolation.

The CSV format is the operator-facing contract — see the template at
backend/data/templates/ilostat_country_template.csv for the canonical shape.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ── Operator metadata schema ───────────────────────────────────────────────

_LANG_TO_SCRIPT = {
    "bn": "bengali",
    "hi": "devanagari",
    "ne": "devanagari",
    "ur": "arabic",
    "ar": "arabic",
    "fa": "arabic",
    "zh": "chinese",
    "ja": "japanese",
    "ko": "hangul",
    "th": "thai",
    "am": "ethiopic",
    "ti": "ethiopic",
}


class CountryMetadata(BaseModel):
    """The 5 required fields + sensible LMIC defaults for the rest."""

    country_name: str = Field(min_length=1)
    country_code: str = Field(min_length=2, max_length=3)
    currency: str = Field(min_length=3, max_length=4)
    usd_rate: float = Field(gt=0)
    primary_language: str = Field(min_length=2, max_length=3)

    secondary_languages: list[str] = Field(default_factory=list)

    youth_unemployment_rate: float = 12.0
    informal_employment_share: float = 75.0
    youth_neet_rate: float = 25.0
    lmic_adjustment_factor: float = Field(default=0.65, gt=0.0, le=1.0)

    @field_validator("country_code", "currency", "primary_language")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper().strip() if v else v

    @field_validator("primary_language")
    @classmethod
    def _lang_lower(cls, v: str) -> str:
        return v.lower().strip()


# ── CSV parsing ────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = (
    "sector_label",
    "isco_group",
    "monthly_wage_local",
    "employment_share_pct",
    "growth_flagged",
)


@dataclass(frozen=True)
class SectorRow:
    sector_label: str
    isco_group: str
    monthly_wage_local: int
    employment_share_pct: float
    growth_flagged: bool


def _to_bool(s: str) -> bool:
    return s.strip().lower() in {"true", "1", "yes", "y", "t"}


def parse_csv(csv_text: str) -> list[SectorRow]:
    """Parse a 5-column CSV into validated SectorRow objects.

    Lines starting with `#` are treated as comments and skipped. Whitespace
    around values is stripped. Raises ValueError with an actionable message
    on missing columns or bad row data.
    """
    # Strip BOM and comment lines before handing to csv.DictReader
    cleaned = "\n".join(
        line for line in csv_text.lstrip("﻿").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not cleaned:
        raise ValueError("CSV is empty (only comments / blank lines).")

    reader = csv.DictReader(io.StringIO(cleaned))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row.")

    headers = [h.strip() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Expected: {list(REQUIRED_COLUMNS)}. Got: {headers}."
        )

    rows: list[SectorRow] = []
    for i, raw in enumerate(reader, start=2):  # start=2 because header is line 1
        try:
            rows.append(
                SectorRow(
                    sector_label=raw["sector_label"].strip(),
                    isco_group=str(raw["isco_group"]).strip(),
                    monthly_wage_local=int(float(raw["monthly_wage_local"])),
                    employment_share_pct=float(raw["employment_share_pct"]),
                    growth_flagged=_to_bool(raw["growth_flagged"]),
                )
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"CSV row {i} is malformed: {e}") from e

    if not rows:
        raise ValueError("CSV has a header but zero data rows.")
    return rows


# ── YAML + JSON builders ───────────────────────────────────────────────────

def _detect_script(primary_language: str) -> str:
    return _LANG_TO_SCRIPT.get(primary_language.lower(), "latin")


# Generic ISCED-aligned ladder used when the operator doesn't supply one.
# Covers the modal LMIC structure (no formal → primary → lower-sec → upper-sec
# → vocational → bachelor → master+).
_DEFAULT_EDUCATION_LEVELS = [
    "None",
    "Primary",
    "Lower secondary",
    "Upper secondary",
    "Vocational",
    "Bachelor",
    "Master+",
]
_DEFAULT_EDUCATION_TO_ISCED = {
    "None": 0,
    "Primary": 1,
    "Lower secondary": 2,
    "Upper secondary": 3,
    "Vocational": 5,
    "Bachelor": 6,
    "Master+": 7,
}

_DEFAULT_OPPORTUNITY_TYPES = [
    "formal_employment",
    "self_employment",
    "gig",
    "training_pathway",
]


@dataclass
class CountryFiles:
    """The three on-disk artefacts produced from one CSV upload."""

    yaml_dict: dict
    labor_json: dict
    opportunities_json: list  # always [] on initial onboarding


def build_country_files(
    csv_text: str,
    metadata: CountryMetadata,
) -> CountryFiles:
    """Top-level entry point. Pure: same inputs → same outputs."""
    rows = parse_csv(csv_text)
    code_lower = metadata.country_code.lower()
    code_upper = metadata.country_code.upper()

    # Build wage_by_sector (USD computed from local + usd_rate).
    wage_by_sector = [
        {
            "sector": r.sector_label,
            "median_monthly_xof": r.monthly_wage_local,  # legacy field name kept for schema compat
            "median_monthly_usd": max(1, round(r.monthly_wage_local / metadata.usd_rate)),
        }
        for r in rows
    ]

    employment_by_sector = [
        {"sector": r.sector_label, "share_pct": r.employment_share_pct}
        for r in rows
    ]

    # ISCO 2-digit → sector label. Multiple rows may share an ISCO group;
    # later rows win (operator decides the canonical mapping by ordering).
    isco_to_sector_mapping = {r.isco_group: r.sector_label for r in rows}

    # Top-3 growth_flagged by employment share (proxy for "where the workers are").
    growth_sectors = sorted(
        (r for r in rows if r.growth_flagged),
        key=lambda r: r.employment_share_pct,
        reverse=True,
    )
    growth_strategic_sectors = [r.sector_label for r in growth_sectors[:3]]

    # ── YAML config ─────────────────────────────────────────────────────
    supported_languages = [metadata.primary_language] + [
        lang.lower() for lang in metadata.secondary_languages
        if lang.lower() != metadata.primary_language
    ]

    yaml_dict = {
        "country": metadata.country_name,
        "country_code": code_upper,
        "ui": {
            "primary_language": metadata.primary_language,
            "supported_languages": supported_languages,
            "script": _detect_script(metadata.primary_language),
        },
        "labor_data": {
            "source_file": f"data/ilostat/{code_lower}_labor_2024.json",
            "currency": metadata.currency,
            "usd_conversion_rate": int(round(metadata.usd_rate)),
            "isco_to_sector_mapping": isco_to_sector_mapping,
            "informal_sector_discount_factor": 0.60,
            "high_value_wage_threshold_usd": 200,
            "growth_strategic_sectors": growth_strategic_sectors,
        },
        "education_taxonomy": {
            "levels": _DEFAULT_EDUCATION_LEVELS,
            "mapping_to_isced": _DEFAULT_EDUCATION_TO_ISCED,
        },
        "automation_calibration": {
            "source": "Frey-Osborne",
            "lmic_adjustment_factor": metadata.lmic_adjustment_factor,
            "rationale": (
                f"Default LMIC adjustment ({metadata.lmic_adjustment_factor}) "
                f"applied to {metadata.country_name}. Refine with country-specific "
                "evidence in production."
            ),
        },
        "opportunities": {
            "source_file": f"data/opportunities/{code_lower}_opportunities.json",
            "types_enabled": _DEFAULT_OPPORTUNITY_TYPES,
        },
        "projections": {
            # Reuse the West Africa projection file as a regional default —
            # same pattern as bangladesh.yaml. Operators can swap later.
            "source_file": "data/wittgenstein/projections_west_africa.json",
        },
    }

    # ── Labor JSON ──────────────────────────────────────────────────────
    labor_json = {
        "country": metadata.country_name,
        "country_code": code_upper,
        "year": datetime.utcnow().year,
        "source": "Operator upload (ILOSTAT-aligned 5-column CSV)",
        "source_url": "https://ilostat.ilo.org/data/",
        "ingested_at": datetime.utcnow().isoformat() + "Z",
        "wage_by_sector": wage_by_sector,
        "employment_by_sector": employment_by_sector,
        "youth_unemployment_rate": metadata.youth_unemployment_rate,
        "informal_employment_share": metadata.informal_employment_share,
        "youth_neet_rate": metadata.youth_neet_rate,
    }

    return CountryFiles(
        yaml_dict=yaml_dict,
        labor_json=labor_json,
        opportunities_json=[],
    )
