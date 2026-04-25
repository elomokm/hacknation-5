"""Module 01 — Skill extractor: raw text → list[ExtractedSkill] via LLM."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from core.models import ExtractedSkill

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5"

_VALID_CATEGORIES = {
    "Mobile Repair", "Web Development", "Digital Literacy", "Carpentry",
    "Welding", "Tailoring", "Driving", "Hospitality", "Agriculture",
    "Healthcare Informal", "Healthcare Formal", "Commerce", "IT Professional",
    "Management", "Finance", "Marketing", "Education", "Engineering",
    "General Service", "Social Work", "Agribusiness", "Other",
}

_SYSTEM = """\
You are a labour market analyst specialized in the West African informal economy.

Your task: extract skills from a person's natural language description of their work or life.

RULES
1. Extract BOTH explicit skills (stated directly) AND implicit skills (clearly inferred from \
described activities). Example: "J'aide ma cousine à gérer son magasin" → implicit: \
customer service, inventory management.
2. Accept any language or code-switching: French, English, Wolof, Fon.
3. Only extract skills backed by clear evidence in the text. Do NOT hallucinate.
4. If the input is too vague or contains no skills, return an empty JSON array: []
5. "I want a job" or similar desires/intentions → 0 skills extracted.

OUTPUT FORMAT: Return ONLY a valid JSON array, no preamble, no markdown fences.
Each element must have exactly these fields:
{
  "raw_label": "exact phrase or close paraphrase from the input",
  "normalized_label": "professional English skill name (2–5 words)",
  "category": one of the allowed categories below,
  "confidence": float 0.0–1.0 (1.0 = explicitly stated with years of experience; \
0.6 = stated without experience context; 0.4 = clearly implied),
  "evidence": "the specific text phrase that supports this extraction"
}

ALLOWED CATEGORIES (use exactly one per skill):
Mobile Repair | Web Development | Digital Literacy | Carpentry | Welding | Tailoring |
Driving | Hospitality | Agriculture | Healthcare Informal | Healthcare Formal | Commerce |
IT Professional | Management | Finance | Marketing | Education | Engineering |
General Service | Social Work | Agribusiness | Other\
"""


def _client() -> anthropic.Anthropic:
    """Return a fresh Anthropic client (reads key at call time)."""
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _build_messages(text: str, image_base64: Optional[str]) -> list[dict]:
    """Assemble the messages list for the API call."""
    user_content: list[dict] | str
    if image_base64:
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64,
                },
            },
            {
                "type": "text",
                "text": (
                    f"Extract skills from this image and the following description.\n\n"
                    f"Description: {text or 'No additional text provided.'}"
                ),
            },
        ]
    else:
        user_content = (
            f"Extract skills from the following description.\n\n"
            f"Description:\n{text}"
        )
    return [{"role": "user", "content": user_content}]


def _parse_response(raw: str) -> list[ExtractedSkill]:
    """Parse the LLM JSON response into validated ExtractedSkill objects."""
    raw = raw.strip()
    # Strip markdown fences if the model added them despite instructions
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("JSON decode failed: %s | raw=%r", exc, raw[:200])
        return []

    if not isinstance(data, list):
        logger.warning("LLM returned non-list JSON: %r", type(data))
        return []

    skills: list[ExtractedSkill] = []
    for item in data:
        # Coerce category to nearest valid value
        if isinstance(item, dict) and item.get("category") not in _VALID_CATEGORIES:
            item["category"] = "Other"
        try:
            skills.append(ExtractedSkill(**item))
        except (ValidationError, TypeError) as exc:
            logger.debug("Skipping invalid skill item: %s — %s", item, exc)
    return skills


def extract_skills(
    text: str,
    image_base64: Optional[str] = None,
) -> list[ExtractedSkill]:
    """Extract structured skills from raw free-text (and optional image).

    Calls claude-sonnet-4-5 once. Returns empty list on any failure.
    """
    if not text and not image_base64:
        return []

    try:
        response = _client().messages.create(
            model=_MODEL,
            max_tokens=1500,
            system=_SYSTEM,
            messages=_build_messages(text, image_base64),
        )
        raw = response.content[0].text if response.content else ""
        skills = _parse_response(raw)
        logger.info(
            "Extracted %d skills from input (%d chars)", len(skills), len(text)
        )
        return skills
    except Exception as exc:
        logger.error("Extraction failed: %s", exc)
        return []
