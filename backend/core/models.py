"""Shared Pydantic v2 models — single source of truth for all UNMAPPED types."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


# ---------------------------------------------------------------------------
# Module 01 — Skill Signal Engine types
# ---------------------------------------------------------------------------

class ExtractedSkill(BaseModel):
    """One skill extracted from raw user input by the LLM."""

    raw_label: str
    normalized_label: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str


class MappedSkill(BaseModel):
    """An ExtractedSkill matched to the ESCO/ISCO taxonomy."""

    esco_id: str
    esco_label: str
    esco_category: str
    isco_groups: list[str]
    isco_titles: list[str]
    match_confidence: float = Field(ge=0.0, le=1.0)
    raw_extraction: ExtractedSkill


class StandardizedProfile(BaseModel):
    """JSON-LD compatible portable skill profile — output of Module 01."""

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field(
        default="https://unmapped.io/v1/context",
        serialization_alias="@context",
    )
    rdf_type: str = Field(default="Person", serialization_alias="@type")
    profile_id: str
    generated_at: datetime
    country_code: str
    name: str
    education: dict
    languages: list[str]
    skills: list[MappedSkill]
    skill_categories: dict[str, int]
    portability: dict
    human_readable_summary: str


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


# ---------------------------------------------------------------------------
# Module 02 — AI Readiness & Displacement Risk types
# ---------------------------------------------------------------------------

class SkillRiskScore(BaseModel):
    """Frey-Osborne automation risk score for one mapped skill."""

    esco_id: str
    esco_label: str
    raw_frey_osborne: Optional[float]
    lmic_adjustment_applied: float
    adjusted_probability: Optional[float]
    risk_band: str  # "low" | "moderate" | "high" | "critical"
    matched_occupations: list[str]
    confidence: str  # "isco_proxy" | "no_match"


class RiskAssessment(BaseModel):
    """Aggregate automation risk assessment for a StandardizedProfile."""

    profile_id: str
    country_code: str
    per_skill_scores: list[SkillRiskScore]
    overall_risk_band: str
    weighted_average_probability: float
    pct_skills_at_risk: float
    methodology_note: str
    limitations: list[str]


class AdjacentSkill(BaseModel):
    """A lower-risk ESCO skill adjacent to a high-risk current skill."""

    esco_id: str
    esco_label: str
    esco_category: str
    automation_risk: SkillRiskScore
    proximity_score: float
    transition_rationale: str


class EducationTrajectory(BaseModel):
    """West Africa education attainment projections from Wittgenstein Centre."""

    region: str
    scenario: str
    timeline: list[ProjectionPoint]
    summary_2025: dict
    summary_2035: dict
    key_shifts: list[str]
