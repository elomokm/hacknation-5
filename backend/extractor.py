import json
import os
from typing import Optional

import anthropic
from pydantic import BaseModel, Field, ValidationError


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """You are a skill extraction expert focused on African informal economies.
Given a description of work or an image of someone working, extract the concrete skills demonstrated.

Return ONLY a JSON array of skill objects. Each object must have:
- name: concise skill name (e.g. "Mobile phone repair", "Inventory management")
- category: one of ["Technical", "Digital", "Commercial", "Craft", "Agricultural", "Service", "Managerial"]
- level: integer 1-5 (1=beginner, 3=intermediate, 5=expert) based on context clues
- confidence: float 0.0-1.0 representing your confidence in this extraction

Return 3-8 skills. No markdown, no explanation — raw JSON array only."""

USER_PROMPT = "Extract skills from this work description:\n\n{text}"
USER_PROMPT_WITH_IMAGE = "Extract skills from this image of work. Additional context: {text}"


class Skill(BaseModel):
    name: str
    category: str
    level: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)


def _parse_skills(raw: str) -> list[Skill]:
    raw = raw.strip()
    # unwrap if Claude returned an object instead of a bare array
    if raw.startswith("{"):
        try:
            obj = json.loads(raw)
            for v in obj.values():
                if isinstance(v, list):
                    raw = json.dumps(v)
                    break
        except json.JSONDecodeError:
            pass
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        skills = []
        for item in data:
            try:
                skills.append(Skill(**item))
            except (ValidationError, TypeError):
                continue
        return skills
    except json.JSONDecodeError:
        return []


def extract_skills(text: str, image_base64: Optional[str] = None) -> list[Skill]:
    try:
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
                    "text": USER_PROMPT_WITH_IMAGE.format(text=text or "No additional context."),
                },
            ]
        else:
            user_content = USER_PROMPT.format(text=text)

        response = _client().messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = next(
            (block.text for block in response.content if block.type == "text"), ""
        )
        return _parse_skills(raw)

    except Exception:
        return []
