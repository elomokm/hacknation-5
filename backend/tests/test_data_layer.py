"""Phase 1 smoke test — validates all data files load and parse against Pydantic models."""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Allow imports from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    AutomationScore,
    ISCOGroup,
    LaborMarketData,
    ProjectionPoint,
    Skill,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def load_and_validate() -> None:
    """Load each data file and validate every record against its Pydantic model."""
    results: dict[str, int] = {}

    # 1 — ESCO skills
    path = DATA_DIR / "esco" / "skills_subset.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    skills = [Skill(**s) for s in raw]
    assert len(skills) >= 140, f"Expected ~150 ESCO skills, got {len(skills)}"
    results["esco/skills_subset.json"] = len(skills)

    # 2 — ISCO groups
    path = DATA_DIR / "isco" / "isco_08_groups.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    groups = [ISCOGroup(**g) for g in raw]
    assert len(groups) >= 35, f"Expected ~39 ISCO groups, got {len(groups)}"
    results["isco/isco_08_groups.json"] = len(groups)

    # 3 — Frey-Osborne automation scores
    path = DATA_DIR / "frey_osborne" / "automation_scores.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    scores = [AutomationScore(**s) for s in raw]
    assert len(scores) >= 45, f"Expected ~50 automation scores, got {len(scores)}"
    probs = [s.automation_probability for s in scores]
    assert all(0.0 <= p <= 1.0 for p in probs), "Automation probability out of [0,1]"
    results["frey_osborne/automation_scores.json"] = len(scores)

    # 4 — Bénin ILOSTAT
    path = DATA_DIR / "ilostat" / "benin_labor_2024.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    benin = LaborMarketData(**raw)
    assert benin.country == "Bénin"
    assert benin.informal_employment_share > 50, "Expected high informality for Bénin"
    results["ilostat/benin_labor_2024.json"] = len(benin.wage_by_sector)

    # 5 — Sénégal ILOSTAT
    path = DATA_DIR / "ilostat" / "senegal_labor_2024.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    senegal = LaborMarketData(**raw)
    assert senegal.country == "Sénégal"
    results["ilostat/senegal_labor_2024.json"] = len(senegal.wage_by_sector)

    # 6 — Wittgenstein projections
    path = DATA_DIR / "wittgenstein" / "projections_west_africa.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    projections = [ProjectionPoint(**p) for p in raw["projections"]]
    assert len(projections) >= 20, f"Expected ≥20 projection points, got {len(projections)}"
    years = {p.year for p in projections}
    assert 2025 in years and 2035 in years, "Missing 2025 or 2035 in projections"
    results["wittgenstein/projections_west_africa.json"] = len(projections)

    # Summary
    logger.info("=" * 50)
    logger.info("Phase 1 data validation — PASSED")
    logger.info("=" * 50)
    for filename, count in results.items():
        logger.info("  %-45s %d records", filename, count)
    logger.info("=" * 50)

    # Extra: show econometric signals that will be visible to jury
    logger.info("Econometric signals preview:")
    logger.info("  Bénin ICT median wage : %d XOF/month (%d USD)",
        next(w.median_monthly_xof for w in benin.wage_by_sector if "ICT" in w.sector),
        next(w.median_monthly_usd for w in benin.wage_by_sector if "ICT" in w.sector))
    logger.info("  Bénin informal share  : %.1f%%", benin.informal_employment_share)
    logger.info("  Sénégal informal share: %.1f%%", senegal.informal_employment_share)
    high_risk = [s for s in scores if s.automation_probability >= 0.85]
    logger.info("  High-risk occupations (≥85%%): %d", len(high_risk))


if __name__ == "__main__":
    load_and_validate()
