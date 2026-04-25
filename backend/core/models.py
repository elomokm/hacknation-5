"""Shared Pydantic v2 models — single source of truth for all UNMAPPED types."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Country config models (Phase 2)
# ---------------------------------------------------------------------------

# Default ISCED-2011 labels (English) — used when a country YAML omits them.
# Per-country override via EducationTaxonomy.isced_labels (e.g. French for BEN/SEN).
_DEFAULT_ISCED_LABELS: dict[int, str] = {
    0: "No formal education",
    1: "Primary education",
    2: "Lower secondary education",
    3: "Upper secondary education",
    4: "Post-secondary non-tertiary",
    5: "Short-cycle tertiary (BTS/DUT)",
    6: "Bachelor's or equivalent",
    7: "Master's or equivalent",
    8: "Doctoral or equivalent",
}

# Default language display names — used when a country YAML omits them.
_DEFAULT_LANG_DISPLAY: dict[str, str] = {
    "fr": "French",
    "en": "English",
    "wo": "Wolof",
    "fon": "Fon",
    "tw": "Twi",
    "ha": "Hausa",
    "ar": "Arabic",
}


class UIConfig(BaseModel):
    """Frontend localisation settings."""

    primary_language: str
    supported_languages: list[str]
    script: str
    # Per-country display names for languages (e.g. {"tw": "Twi"}).
    # Falls back to _DEFAULT_LANG_DISPLAY when omitted.
    language_display_names: dict[str, str] = Field(default_factory=dict)

    def display_name_for(self, code: str) -> str:
        """Return the human-readable display name for a language code."""
        if code in self.language_display_names:
            return self.language_display_names[code]
        return _DEFAULT_LANG_DISPLAY.get(code, code.upper())


class LaborDataConfig(BaseModel):
    """Reference to ILOSTAT data file, currency, and country-specific
    economic constants. Every value here is an INPUT to UNMAPPED — there
    is no Python-side hardcoded equivalent.
    """

    source_file: str
    currency: str
    usd_conversion_rate: int

    # ISCO 2-digit code → sector label (must match labels in source_file JSON).
    # If empty, EconometricSignals uses _DEFAULT_ISCO_TO_SECTOR (West Africa).
    isco_to_sector_mapping: dict[str, str] = Field(default_factory=dict)

    # Informal worker income ≈ formal sector median × this factor.
    # Varies 0.40–0.75 across LMICs (informality gap).
    informal_sector_discount_factor: float = Field(default=0.60, gt=0.0, le=1.0)

    # Sectors with median wage above this threshold are flagged "high-value".
    high_value_wage_threshold_usd: int = Field(default=200, gt=0)

    # Strategic growth sectors flagged in the policymaker dashboard.
    # Defaults to West Africa default (ICT + Finance) when omitted.
    growth_strategic_sectors: list[str] = Field(default_factory=list)


class EducationTaxonomy(BaseModel):
    """Local education ladder with ISCED-2011 equivalence map."""

    levels: list[str]
    mapping_to_isced: dict[str, int]
    # Per-country ISCED labels (e.g. localised in FR for BEN/SEN).
    # Keys are ISCED codes (0-8), values are human-readable labels.
    # Falls back to _DEFAULT_ISCED_LABELS when omitted.
    isced_labels: dict[int, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def levels_covered_by_mapping(self) -> "EducationTaxonomy":
        """All levels must have an ISCED mapping."""
        missing = [lvl for lvl in self.levels if lvl not in self.mapping_to_isced]
        if missing:
            raise ValueError(f"Education levels missing ISCED mapping: {missing}")
        return self

    def label_for(self, isced_code: int) -> str:
        """Return the ISCED label, falling back to the default English set."""
        if isced_code in self.isced_labels:
            return self.isced_labels[isced_code]
        return _DEFAULT_ISCED_LABELS.get(isced_code, "Unknown")


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
