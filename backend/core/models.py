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
    """Opportunity configuration per country."""

    source_file: str
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

    model_config = ConfigDict(extra="allow")  # tolerate extra JSON fields

    country: str
    year: int
    source: str
    wage_by_sector: list[WageSector]
    employment_by_sector: list[EmploymentSector]
    youth_unemployment_rate: float
    informal_employment_share: float
    youth_neet_rate: Optional[float] = None


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
    """A realistic local economic opportunity (loaded from country JSON)."""

    id: str
    type: str
    title: str
    title_local: str
    sector: str
    required_skills_isco: list[str]
    required_skills_esco: list[str]
    education_min: str
    experience_years_min: int
    wage_range_xof: list[int]
    geography: str
    remote_eligible: bool
    description: str
    training_url: Optional[str]
    realistic_for_youth: bool


class OpportunityMatch(BaseModel):
    """A profile-to-opportunity match with econometric signals."""

    opportunity: Opportunity
    fit_score: float = Field(ge=0.0, le=1.0)
    matched_isco: list[str]
    gap_skills: list[str]
    gap_education: Optional[str]
    wage_delta: dict
    accessibility_note: str


class WageSignal(BaseModel):
    """Econometric signal 1 — wage floor and income gap."""

    current_estimated_xof: int
    current_estimated_usd: int
    formal_median_xof_by_sector: dict[str, int]
    wage_gap_to_best_match_xof: int
    wage_gap_multiplier: float
    methodology_note: str


class SectorGrowthSignal(BaseModel):
    """Econometric signal 2 — sector employment share and value flags."""

    sectors: list[dict]
    growth_flagged_sectors: list[str]
    methodology_note: str


class YouthDashboard(BaseModel):
    """Assembled youth-facing dashboard combining all 3 modules."""

    profile_summary: str
    top_3_opportunities: list[OpportunityMatch]
    wage_mirror: dict
    risk_summary: dict
    next_steps: list[str]
    transparency_notes: list[str]


class PolicymakerDashboard(BaseModel):
    """Policymaker-facing aggregate dashboard."""

    country: str
    aggregate_skill_distribution: dict
    aggregate_isco_distribution: dict
    youth_unemployment: float
    youth_neet: float
    informal_share: float
    automation_risk_aggregate: dict
    skill_gaps_by_sector: list[dict]
    recommended_program_areas: list[str]


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
