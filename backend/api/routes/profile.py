"""Module 01 — Skill extraction and profile generation endpoints."""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.dependencies import (
    PROFILE_STORE,
    get_country_config,
    get_mapper,
    get_profile_or_404,
)
from core.models import ExtractedSkill, MappedSkill, StandardizedProfile
from module_01_skills.extractor import extract_skills
from module_01_skills.profile_generator import generate_profile

router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────
class ExtractRequest(BaseModel):
    text: str
    image_base64: Optional[str] = None
    country_code: str = "BEN"


class ExtractResponse(BaseModel):
    extracted_skills: list[ExtractedSkill]
    mapped_skills: list[MappedSkill]
    country_code: str
    unmapped_count: int


class GenerateProfileRequest(BaseModel):
    user_name: str
    text: str
    education_level: str
    languages: list[str]
    country_code: str = "BEN"


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/extract",
    response_model=ExtractResponse,
    summary="Extract skills from text",
    description=(
        "Run claude-sonnet-4-5 to extract skills from natural-language input "
        "(any language), then map to ESCO taxonomy. Returns both extracted and mapped."
    ),
)
async def extract(req: ExtractRequest) -> ExtractResponse:
    """Extract + map skills in one call (no profile creation)."""
    get_country_config(req.country_code)  # validate country exists
    mapper = get_mapper()

    extracted = extract_skills(req.text, req.image_base64)
    mapped = mapper.map_skills_batch(extracted)

    return ExtractResponse(
        extracted_skills=extracted,
        mapped_skills=mapped,
        country_code=req.country_code.upper(),
        unmapped_count=len(extracted) - len(mapped),
    )


@router.post(
    "/generate",
    response_model=StandardizedProfile,
    response_model_by_alias=True,
    summary="Generate full StandardizedProfile",
    description=(
        "Full Module 01 pipeline: extract → map → generate JSON-LD profile. "
        "Profile is stored in-memory (MVP) and returned. "
        "Use the profile_id for downstream risk + opportunity calls."
    ),
)
async def generate(req: GenerateProfileRequest) -> StandardizedProfile:
    """Generate, store, and return a StandardizedProfile."""
    config = get_country_config(req.country_code)
    mapper = get_mapper()

    extracted = extract_skills(req.text)
    mapped = mapper.map_skills_batch(extracted)

    profile = generate_profile(
        user_id=str(uuid4()),
        user_name=req.user_name,
        education_level=req.education_level,
        languages=req.languages,
        extracted_skills=extracted,
        mapped_skills=mapped,
        config=config,
    )

    PROFILE_STORE[profile.profile_id] = profile
    return profile


@router.get(
    "/{profile_id}",
    response_model=StandardizedProfile,
    response_model_by_alias=True,
    summary="Retrieve stored profile",
)
async def get_profile(profile_id: str) -> StandardizedProfile:
    """Return a previously generated profile by ID."""
    return get_profile_or_404(profile_id)


@router.get(
    "/{profile_id}/jsonld",
    summary="Profile as JSON-LD",
    description=(
        "Returns the profile with @context and @type fields, "
        "served as application/ld+json. Anyone can consume this."
    ),
)
async def get_profile_jsonld(profile_id: str) -> JSONResponse:
    """Return the profile as JSON-LD with proper Content-Type."""
    profile = get_profile_or_404(profile_id)
    return JSONResponse(
        content=profile.model_dump(mode="json", by_alias=True),
        media_type="application/ld+json",
    )
