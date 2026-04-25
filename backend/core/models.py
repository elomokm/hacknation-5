"""Shared Pydantic v2 models — single source of truth for all UNMAPPED types."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Country config models (Phase 2)
# ---------------------------------------------------------------------------

class UIConfig(BaseModel):
    """Frontend localisation settings."""

    primary_language: str
    supported_languages: list[str]
    script: str


class LaborDataConfig(BaseModel):
    """Reference to ILOSTAT data file and currency settings."""

    source_file: str
    currency: str
    usd_conversion_rate: int


class EducationTaxonomy(BaseModel):
    """Local education ladder with ISCED-2011 equivalence map."""

    levels: list[str]
    mapping_to_isced: dict[str, int]

    @model_validator(mode="after")
    def levels_covered_by_mapping(self) -> "EducationTaxonomy":
        """All levels must have an ISCED mapping."""
        missing = [lvl for lvl in self.levels if lvl not in self.mapping_to_isced]
        if missing:
            raise ValueError(f"Education levels missing ISCED mapping: {missing}")
        return self


class AutomationCalibration(BaseModel):
    """Frey-Osborne LMIC adjustment settings."""

    source: str
    lmic_adjustment_factor: float = Field(gt=0.0, le=1.0)
    rationale: str


class OpportunitiesConfig(BaseModel):
    """Which opportunity types are enabled for this country."""

    types_enabled: list[str]


class ProjectionsConfig(BaseModel):
    """Reference to Wittgenstein projection data file."""

    source_file: str


class CountryConfig(BaseModel):
    """Full country configuration — loaded from YAML at runtime."""

    country: str
    country_code: str
    ui: UIConfig
    labor_data: LaborDataConfig
    education_taxonomy: EducationTaxonomy
    automation_calibration: AutomationCalibration
    opportunities: OpportunitiesConfig
    projections: ProjectionsConfig


class Skill(BaseModel):
    """ESCO-aligned skill entry."""

    esco_id: str
    label: str
    category: str
    description: str
    isco_groups: list[str]


class ISCOGroup(BaseModel):
    """ISCO-08 occupational group (2-digit level)."""

    code: str
    title: str
    level: int
    description: str


class AutomationScore(BaseModel):
    """Frey-Osborne automation probability for one occupation."""

    occupation: str
    isco_match: str
    automation_probability: float = Field(ge=0.0, le=1.0)
    source: str = "Frey-Osborne 2017"


class WageSector(BaseModel):
    """Wage data for one sector from ILOSTAT."""

    sector: str
    median_monthly_xof: int
    median_monthly_usd: int


class EmploymentSector(BaseModel):
    """Employment share by sector from ILOSTAT."""

    sector: str
    share_pct: float


class LaborMarketData(BaseModel):
    """Full ILOSTAT country snapshot."""

    country: str
    year: int
    source: str
    wage_by_sector: list[WageSector]
    employment_by_sector: list[EmploymentSector]
    youth_unemployment_rate: float
    informal_employment_share: float


class ProjectionPoint(BaseModel):
    """Single Wittgenstein education projection data point."""

    year: int
    education_level: str
    share_youth_pct: float


class StandardizedProfile(BaseModel):
    """JSON-LD compatible skill profile — the output of Module 01."""

    profile_id: str
    country_code: str
    raw_description: str
    extracted_skills: list[Skill]
    isco_matches: list[str]
    created_at: str


class RiskAssessment(BaseModel):
    """Automation and upskilling risk output from Module 02."""

    profile_id: str
    automation_risk: float = Field(ge=0.0, le=1.0)
    lmic_adjusted_risk: float = Field(ge=0.0, le=1.0)
    adjacent_skills: list[str]
    risk_label: str  # "low" | "medium" | "high"


class Opportunity(BaseModel):
    """A local economic opportunity entry."""

    id: str
    title: str
    sector: str
    isco_code: str
    type: str  # "formal_employment" | "self_employment" | "gig" | "training_pathway"
    median_monthly_usd: int
    required_skills: list[str]


class MatchResult(BaseModel):
    """Ranked opportunity match with econometric signals."""

    opportunity: Opportunity
    match_score: float = Field(ge=0.0, le=1.0)
    income_delta_usd: int
    pathway_steps: list[str]
    automation_risk: float
    econometric_signals: dict
