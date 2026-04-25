"""Module 01 — Taxonomy mapper: ExtractedSkill → MappedSkill via ESCO/ISCO lookup.

No LLM calls. Pure keyword-overlap algorithm with category boost.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from core.models import ExtractedSkill, MappedSkill, ISCOGroup, Skill

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

_STOP: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "to", "for", "with",
    "by", "on", "at", "is", "are", "be", "its", "this", "that",
    "basic", "general", "advanced", "junior", "senior",
    "skill", "ability", "knowledge", "competence",
})

_MATCH_THRESHOLD = 0.35
_CATEGORY_BOOST = 0.20


def _stem(word: str) -> str:
    """Crude 5-char prefix stem — improves token matching across inflections."""
    return word[:5] if len(word) > 5 else word


def _normalize(text: str) -> set[str]:
    """Tokenise, lowercase, remove stop words, apply stem."""
    tokens = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    return {_stem(t) for t in tokens if t not in _STOP and len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


class TaxonomyMapper:
    """Maps extracted skills to ESCO/ISCO taxonomy using keyword overlap."""

    def __init__(self) -> None:
        """Load ESCO skills and ISCO groups once at init time."""
        self._esco: list[Skill] = self._load_esco()
        self._isco_index: dict[str, str] = self._load_isco_index()
        # Pre-compute normalised tokens for each ESCO label (fast lookup)
        self._esco_tokens: list[set[str]] = [
            _normalize(s.label) for s in self._esco
        ]
        logger.info(
            "TaxonomyMapper ready: %d ESCO skills, %d ISCO groups",
            len(self._esco),
            len(self._isco_index),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def map_skill(self, extracted: ExtractedSkill) -> Optional[MappedSkill]:
        """Map one ExtractedSkill to its best ESCO match.

        Returns None if no match exceeds the confidence threshold.
        """
        # Only use normalized_label (English) — raw_label may be in any language
        # and adding it would dilute Jaccard against English ESCO labels.
        query_tokens = _normalize(extracted.normalized_label)

        best_score = 0.0
        best_idx = -1

        for idx, esco_tokens in enumerate(self._esco_tokens):
            score = _jaccard(query_tokens, esco_tokens)
            if self._esco[idx].category == extracted.category:
                score += _CATEGORY_BOOST
            score = min(score, 1.0)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx < 0 or best_score < _MATCH_THRESHOLD:
            logger.debug(
                "No ESCO match for %r (best=%.3f < threshold=%.2f)",
                extracted.normalized_label,
                best_score,
                _MATCH_THRESHOLD,
            )
            return None

        esco = self._esco[best_idx]
        isco_titles = [
            self._isco_index.get(code, f"ISCO {code}")
            for code in esco.isco_groups
        ]
        return MappedSkill(
            esco_id=esco.esco_id,
            esco_label=esco.label,
            esco_category=esco.category,
            isco_groups=esco.isco_groups,
            isco_titles=isco_titles,
            match_confidence=round(best_score, 3),
            raw_extraction=extracted,
        )

    def map_skills_batch(
        self, extracted: list[ExtractedSkill]
    ) -> list[MappedSkill]:
        """Map a list of ExtractedSkills; drops skills with no ESCO match."""
        mapped: list[MappedSkill] = []
        for skill in extracted:
            result = self.map_skill(skill)
            if result is not None:
                mapped.append(result)
        logger.info(
            "Mapped %d / %d extracted skills to ESCO",
            len(mapped),
            len(extracted),
        )
        return mapped

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_esco(self) -> list[Skill]:
        """Load ESCO skills subset from JSON."""
        path = _DATA_DIR / "esco" / "skills_subset.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Skill(**s) for s in raw]

    def _load_isco_index(self) -> dict[str, str]:
        """Return {isco_code: title} index from ISCO-08 groups JSON."""
        path = _DATA_DIR / "isco" / "isco_08_groups.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        groups = [ISCOGroup(**g) for g in raw]
        return {g.code: g.title for g in groups}
