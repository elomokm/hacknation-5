"""API integration tests using FastAPI TestClient.

Some tests use real LLM calls (extract, generate). They are gated on the
ANTHROPIC_API_KEY env var — if missing, those tests are skipped with a clear note.
"""

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

_HAS_API_KEY = bool(os.getenv("ANTHROPIC_API_KEY"))
_DIV = "=" * 65


def test_health_check():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["service"] == "UNMAPPED API"
    logger.info("✓ /api/health → %s", body)


def test_info_endpoint():
    r = client.get("/api/info")
    assert r.status_code == 200
    body = r.json()
    assert "modules" in body
    assert len(body["modules"]) == 3
    assert "BEN" in body["supported_countries"]
    assert "SEN" in body["supported_countries"]
    logger.info("✓ /api/info → %d modules, %d countries", len(body["modules"]), len(body["supported_countries"]))


def test_list_countries():
    r = client.get("/api/config/countries")
    assert r.status_code == 200
    countries = r.json()
    codes = {c["code"] for c in countries}
    # Four countries spanning two regions (West Africa + South Asia) prove
    # auto-discovery + cross-regional infrastructure claim.
    assert {"BEN", "SEN", "GHA", "BGD"}.issubset(codes)
    # Different countries → different LMIC factors → proves localizability
    by_code = {c["code"]: c for c in countries}
    assert by_code["BEN"]["lmic_adjustment_factor"] != by_code["SEN"]["lmic_adjustment_factor"]
    assert by_code["GHA"]["lmic_adjustment_factor"] != by_code["BEN"]["lmic_adjustment_factor"]
    logger.info("✓ /api/config/countries → %d countries (BEN, SEN, GHA) with distinct LMIC factors", len(countries))


def test_reload_endpoint():
    """POST /api/config/reload re-scans configs/ directory."""
    r = client.post("/api/config/reload")
    assert r.status_code == 200
    body = r.json()
    assert "countries" in body
    assert "GHA" in body["countries"]  # Ghana auto-discovered after reload
    assert body["count"] == len(body["countries"])
    logger.info("✓ /api/config/reload → %d countries re-discovered: %s", body["count"], body["countries"])


def test_get_ghana_config():
    """Ghana config — proof that adding 3 files = working country, no Python edits."""
    r = client.get("/api/config/GHA")
    assert r.status_code == 200, r.text
    gha = r.json()
    assert gha["country_code"] == "GHA"
    assert gha["country"] == "Ghana"
    assert gha["ui"]["primary_language"] == "en"
    assert gha["labor_data"]["currency"] == "GHS"
    # New config-driven fields surface via API
    assert len(gha["labor_data"]["isco_to_sector_mapping"]) >= 30
    assert "Mining and quarrying" in gha["labor_data"]["growth_strategic_sectors"]
    logger.info("✓ /api/config/GHA → %s (en, GHS, %d ISCO mappings)",
                gha["country"], len(gha["labor_data"]["isco_to_sector_mapping"]))


def test_ghana_signals_endpoint():
    """Ghana econometric signals — different currency, different strategic sectors."""
    r = client.get("/api/opportunities/GHA/signals")
    assert r.status_code == 200, r.text
    body = r.json()
    growth_flagged = body["growth"]["growth_flagged_sectors"]
    # Ghana flags Mining as strategic — Bénin doesn't
    assert any("Mining" in s for s in growth_flagged), \
        f"Ghana should flag Mining as strategic, got: {growth_flagged}"
    logger.info("✓ /api/opportunities/GHA/signals → strategic: %s", growth_flagged)


def test_opportunity_ingestion_lifecycle():
    """Operator-facing ingestion: upsert → bulk → delete, with cache invalidation.

    This is the end-to-end proof: an operator can push their own opportunity
    data via HTTP without touching the codebase. UNMAPPED standardizes,
    matches, and surfaces it on the next /match call.
    """
    # Get current count
    r = client.get("/api/opportunities/BEN")
    assert r.status_code == 200
    initial_count = len(r.json())
    logger.info("Initial BEN opportunities: %d", initial_count)

    # 1. UPSERT a brand-new opportunity (operator: a Cotonou NGO)
    new_opp = {
        "id": "test_ingestion_001",
        "type": "self_employment",
        "title": "Solar Pump Maintenance Technician",
        "title_local": "Technicien Maintenance Pompe Solaire",
        "sector": "Construction",
        "required_skills_isco": ["74", "71"],
        "required_skills_esco": ["esco:skill:0007"],
        "education_min": "BEPC",
        "experience_years_min": 1,
        "wage_range_xof": [70000, 130000],
        "geography": "Pan-Bénin",
        "remote_eligible": False,
        "description": "Maintain solar irrigation pumps in northern Bénin.",
        "training_url": None,
        "realistic_for_youth": True,
    }
    r = client.post("/api/opportunities/BEN/upsert", json=new_opp)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 1
    assert body["updated"] == 0
    assert body["total_in_country"] == initial_count + 1
    logger.info("✓ /opportunities/BEN/upsert (new) → +1, total=%d", body["total_in_country"])

    # 2. UPSERT same id with updated fields → should UPDATE not insert
    new_opp["wage_range_xof"] = [80000, 140000]
    r = client.post("/api/opportunities/BEN/upsert", json=new_opp)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 0
    assert body["updated"] == 1
    assert body["total_in_country"] == initial_count + 1  # unchanged
    logger.info("✓ /opportunities/BEN/upsert (existing) → updated, total still %d", body["total_in_country"])

    # 3. BULK upsert: 1 new + 1 update of the existing
    bulk_payload = {
        "opportunities": [
            new_opp,  # update again
            {
                **new_opp,
                "id": "test_ingestion_002",
                "title": "Borehole Drilling Assistant",
                "title_local": "Assistant Forage Puits",
            },
        ]
    }
    r = client.post("/api/opportunities/BEN/bulk", json=bulk_payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 1
    assert body["updated"] == 1
    assert body["total_in_country"] == initial_count + 2
    logger.info("✓ /opportunities/BEN/bulk → +1 ins, 1 upd, total=%d", body["total_in_country"])

    # 4. DELETE both
    for opp_id in ("test_ingestion_001", "test_ingestion_002"):
        r = client.delete(f"/api/opportunities/BEN/{opp_id}")
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] == 1

    # 5. Verify back to initial count
    r = client.get("/api/opportunities/BEN")
    final_count = len(r.json())
    assert final_count == initial_count, \
        f"Cleanup failed: started {initial_count}, ended {final_count}"
    logger.info("✓ Lifecycle complete: %d → %d → %d (clean)",
                initial_count, initial_count + 2, final_count)

    # 6. DELETE non-existent → 404
    r = client.delete("/api/opportunities/BEN/does_not_exist_999")
    assert r.status_code == 404
    logger.info("✓ DELETE non-existent → 404")


def test_bangladesh_cross_regional():
    """Bangladesh proves cross-regional infrastructure (South Asia, bengali script)."""
    r = client.get("/api/config/BGD")
    assert r.status_code == 200, r.text
    bgd = r.json()
    assert bgd["country"] == "Bangladesh"
    assert bgd["ui"]["primary_language"] == "bn"
    assert bgd["ui"]["script"] == "bengali"  # multi-script proof
    assert bgd["labor_data"]["currency"] == "BDT"
    logger.info(
        "✓ /api/config/BGD → %s | script=%s | %s",
        bgd["country"], bgd["ui"]["script"], bgd["labor_data"]["currency"],
    )

    # Bangladesh-specific strategic sector
    r = client.get("/api/opportunities/BGD/signals")
    assert r.status_code == 200, r.text
    body = r.json()
    growth_flagged = body["growth"]["growth_flagged_sectors"]
    assert any("Garment" in s for s in growth_flagged), \
        f"Bangladesh should flag Garment manufacturing (RMG) as strategic, got: {growth_flagged}"
    logger.info("✓ /api/opportunities/BGD/signals → strategic: %s", growth_flagged)


def test_get_config_BEN_and_SEN():
    """The localizability proof — same endpoint, different country = different config, no code change."""
    ben = client.get("/api/config/BEN").json()
    sen = client.get("/api/config/SEN").json()

    assert ben["country_code"] == "BEN"
    assert sen["country_code"] == "SEN"
    assert ben["country"] == "Bénin"
    assert sen["country"] == "Sénégal"
    # BEPC vs BFEM — country-specific education ladders
    assert "BEPC" in ben["education_taxonomy"]["levels"]
    assert "BFEM" in sen["education_taxonomy"]["levels"]
    logger.info("✓ Config switching proven: BEN(BEPC) vs SEN(BFEM)")


def test_invalid_country_returns_structured_error():
    r = client.get("/api/config/XYZ")
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "ValueError"
    assert body["module"] == "core_config"
    assert "Unknown country code" in body["detail"]
    logger.info("✓ Invalid country returns structured 400 with module=%r", body["module"])


def test_get_schema():
    r = client.get("/api/config/schema")
    assert r.status_code == 200
    body = r.json()
    assert "schema" in body
    assert "how_to_add_country" in body
    assert len(body["how_to_add_country"]) >= 3
    logger.info("✓ /api/config/schema returns CountryConfig schema + onboarding guide")


def test_projections_endpoint():
    r = client.get("/api/risk/projections/BEN")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "West Africa"
    assert "summary_2025" in body
    assert "summary_2035" in body
    assert len(body["key_shifts"]) >= 1
    logger.info("✓ /api/risk/projections/BEN → %d key shifts", len(body["key_shifts"]))


def test_signals_endpoint():
    """Signals endpoint must work without a profile (population-level)."""
    r = client.get("/api/opportunities/BEN/signals")
    assert r.status_code == 200
    body = r.json()
    assert "wage" in body
    assert "growth" in body
    assert body["wage"]["current_estimated_xof"] > 0
    assert len(body["growth"]["sectors"]) >= 5
    logger.info(
        "✓ /api/opportunities/BEN/signals → wage est %d XOF, %d sectors",
        body["wage"]["current_estimated_xof"],
        len(body["growth"]["sectors"]),
    )


def test_policymaker_dashboard():
    r = client.get("/api/opportunities/BEN/dashboard/policymaker")
    assert r.status_code == 200
    body = r.json()
    assert body["country"] == "Bénin"
    assert body["informal_share"] > 50
    assert len(body["recommended_program_areas"]) >= 2
    logger.info("✓ Policymaker dashboard: informal=%.1f%%, %d programs",
                body["informal_share"], len(body["recommended_program_areas"]))


def test_full_pipeline_via_api():
    """End-to-end: extract → generate → risk → match (uses live API)."""
    if not _HAS_API_KEY:
        logger.warning("⏭ Skipping full pipeline test — no ANTHROPIC_API_KEY in env")
        return

    text = (
        "Je m'appelle Akossiwa. J'ai un BEPC. Je répare des téléphones "
        "depuis 4 ans à Cotonou. J'ai appris HTML sur YouTube. "
        "J'aide ma cousine à gérer son magasin, je tiens son inventaire sur Excel."
    )

    # 1 — generate profile
    r = client.post("/api/profile/generate", json={
        "user_name": "Akossiwa",
        "text": text,
        "education_level": "BEPC",
        "languages": ["fr", "fon"],
        "country_code": "BEN",
    })
    assert r.status_code == 200, r.text
    profile = r.json()
    assert profile["@context"]
    assert profile["@type"] == "Person"
    assert profile["country_code"] == "BEN"
    assert len(profile["skills"]) >= 2
    profile_id = profile["profile_id"]
    logger.info("✓ /profile/generate → profile_id=%s, %d mapped skills", profile_id, len(profile["skills"]))

    # 2 — risk assessment
    r = client.post("/api/risk/assess", json={
        "profile_id": profile_id,
        "country_code": "BEN",
        "include_adjacent": True,
    })
    assert r.status_code == 200, r.text
    risk_resp = r.json()
    assert "assessment" in risk_resp
    assert risk_resp["assessment"]["overall_risk_band"] in {"low", "moderate", "high", "critical", "no_match"}
    logger.info(
        "✓ /risk/assess → band=%s, %d adjacent buckets",
        risk_resp["assessment"]["overall_risk_band"],
        len(risk_resp["adjacent_skills"]),
    )

    # 3 — match opportunities
    r = client.post("/api/opportunities/match", json={
        "profile_id": profile_id,
        "country_code": "BEN",
        "top_k": 5,
    })
    assert r.status_code == 200, r.text
    match_resp = r.json()
    assert len(match_resp["matches"]) >= 1
    assert "wage_signal" in match_resp
    assert "growth_signal" in match_resp
    logger.info("✓ /opportunities/match → %d matches", len(match_resp["matches"]))

    # 4 — youth dashboard
    r = client.get(f"/api/opportunities/BEN/dashboard/youth?profile_id={profile_id}")
    assert r.status_code == 200, r.text
    dashboard = r.json()
    assert "wage_mirror" in dashboard
    assert "next_steps" in dashboard
    assert len(dashboard["next_steps"]) >= 2
    logger.info("✓ /dashboard/youth → wage mirror x%.1f", dashboard["wage_mirror"]["multiplier"])

    # 5 — JSON-LD profile retrieval
    r = client.get(f"/api/profile/{profile_id}/jsonld")
    assert r.status_code == 200
    assert "ld+json" in r.headers["content-type"]
    body = r.json()
    assert body["@context"]
    logger.info("✓ /profile/{id}/jsonld served as application/ld+json")


if __name__ == "__main__":
    logger.info(_DIV)
    logger.info("UNMAPPED API — TestClient suite")
    logger.info(_DIV)

    test_health_check()
    test_info_endpoint()
    test_list_countries()
    test_get_config_BEN_and_SEN()
    test_get_ghana_config()
    test_reload_endpoint()
    test_invalid_country_returns_structured_error()
    test_get_schema()
    test_projections_endpoint()
    test_signals_endpoint()
    test_ghana_signals_endpoint()
    test_bangladesh_cross_regional()
    test_opportunity_ingestion_lifecycle()
    test_policymaker_dashboard()
    test_full_pipeline_via_api()

    logger.info("")
    logger.info(_DIV)
    logger.info("ALL API TESTS PASSED")
    logger.info(_DIV)
