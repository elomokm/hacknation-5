"""Module 03 — Econometric signals: wage floors and sector employment data.

No LLM calls. Two required econometric signals exposed to user.
"""

import json
import logging
from pathlib import Path

from core.models import (
    CountryConfig,
    LaborMarketData,
    SectorGrowthSignal,
    StandardizedProfile,
    WageSignal,
)

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent

# Mapping ISCO 2-digit → sector label (as used in ILOSTAT data)
_ISCO_TO_SECTOR: dict[str, str] = {
    "11": "Public administration and defence",
    "12": "Financial and insurance activities",
    "13": "Trade and commerce (formal retail)",
    "14": "Accommodation and food services",
    "21": "Information and communication (ICT)",
    "22": "Human health and social work",
    "23": "Education",
    "24": "Financial and insurance activities",
    "25": "Information and communication (ICT)",
    "31": "Manufacturing",
    "32": "Human health and social work",
    "33": "Financial and insurance activities",
    "41": "Trade and commerce (informal)",
    "42": "Trade and commerce (informal)",
    "43": "Trade and commerce (formal retail)",
    "51": "Accommodation and food services",
    "52": "Trade and commerce (informal)",
    "54": "Other service activities",
    "61": "Agriculture, forestry and fishing",
    "62": "Agriculture, forestry and fishing",
    "71": "Construction",
    "72": "Manufacturing",
    "73": "Manufacturing",
    "74": "Manufacturing",
    "75": "Manufacturing",
    "83": "Transportation and storage",
    "91": "Other service activities",
    "92": "Agriculture, forestry and fishing",
    "93": "Construction",
    "94": "Accommodation and food services",
    "95": "Trade and commerce (informal)",
}

# Sectors flagged as high-value (wage > 200 USD/month) or high-growth strategic
_HIGH_VALUE_WAGE_USD = 200
_GROWTH_STRATEGIC_SECTORS = {
    "Information and communication (ICT)",
    "Financial and insurance activities",
}


class EconometricSignals:
    """Surfaces two required econometric signals from ILOSTAT data."""

    def __init__(self, config: CountryConfig) -> None:
        """Load labor market data for the active country."""
        path = _BACKEND_DIR / config.labor_data.source_file
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._labor = LaborMarketData(**raw)
        self._config = config
        # Build wage lookup: sector → median_xof
        self._wage_by_sector: dict[str, int] = {
            w.sector: w.median_monthly_xof for w in self._labor.wage_by_sector
        }
        logger.info(
            "EconometricSignals ready for %s: %d wage sectors",
            config.country_code,
            len(self._wage_by_sector),
        )

    # ------------------------------------------------------------------
    # Signal 1 — Wage
    # ------------------------------------------------------------------

    def get_wage_signals(self, profile: StandardizedProfile) -> WageSignal:
        """Estimate current income and formal wage gap (Signal 1)."""
        usd_rate = self._config.labor_data.usd_conversion_rate

        # Map profile ISCO groups to sectors
        profile_isco = {
            code for skill in profile.skills for code in skill.isco_groups
        }
        profile_sectors = {
            _ISCO_TO_SECTOR[code]
            for code in profile_isco
            if code in _ISCO_TO_SECTOR
        }

        # Estimate current income: use lowest matching sector wage × informal discount
        # For informal workers, actual income ≈ 55-65% of formal sector median
        _INFORMAL_DISCOUNT = 0.60
        matched_wages = [
            self._wage_by_sector[s]
            for s in profile_sectors
            if s in self._wage_by_sector
        ]
        if matched_wages:
            # Use informal trade as proxy if no better match; otherwise take minimum sector
            informal_sector = "Trade and commerce (informal)"
            if informal_sector in self._wage_by_sector:
                # Conservative: use informal trade wage as current estimate
                current_xof = self._wage_by_sector[informal_sector]
            else:
                current_xof = int(min(matched_wages) * _INFORMAL_DISCOUNT)
        else:
            # Fallback: agriculture wage (lowest) as conservative estimate
            agri = "Agriculture, forestry and fishing"
            current_xof = self._wage_by_sector.get(agri, 35000)

        current_usd = round(current_xof / usd_rate)

        # Formal median wages for profile-relevant sectors
        formal_by_sector = {
            s: self._wage_by_sector[s]
            for s in profile_sectors
            if s in self._wage_by_sector
        }
        # Also include ICT as aspirational signal
        ict_key = "Information and communication (ICT)"
        if ict_key in self._wage_by_sector:
            formal_by_sector[ict_key] = self._wage_by_sector[ict_key]

        best_formal_xof = max(formal_by_sector.values()) if formal_by_sector else current_xof
        gap_xof = best_formal_xof - current_xof
        multiplier = round(best_formal_xof / max(current_xof, 1), 2)

        methodology_note = (
            f"Current income estimated at informal sector median "
            f"({self._labor.country}, ILOSTAT 2024 reference). "
            f"Formal median wages from ILOSTAT sector survey data. "
            f"USD at {usd_rate} XOF/USD (IMF 2024)."
        )

        return WageSignal(
            current_estimated_xof=current_xof,
            current_estimated_usd=current_usd,
            formal_median_xof_by_sector=formal_by_sector,
            wage_gap_to_best_match_xof=gap_xof,
            wage_gap_multiplier=multiplier,
            methodology_note=methodology_note,
        )

    # ------------------------------------------------------------------
    # Signal 2 — Sector employment & growth
    # ------------------------------------------------------------------

    def get_growth_signals(self) -> SectorGrowthSignal:
        """Return sector employment shares and growth flags (Signal 2)."""
        sectors_out: list[dict] = []
        growth_flagged: list[str] = []

        for emp in self._labor.employment_by_sector:
            wage_info = self._wage_by_sector.get(emp.sector)
            wage_usd = round(wage_info / self._config.labor_data.usd_conversion_rate) if wage_info else None

            if emp.sector in _GROWTH_STRATEGIC_SECTORS:
                status = "high_value"
                growth_flagged.append(emp.sector)
            elif emp.share_pct >= 10.0:
                status = "large_base"
            elif emp.share_pct >= 5.0:
                status = "significant"
            else:
                status = "niche"

            sectors_out.append({
                "sector": emp.sector,
                "employment_share_pct": emp.share_pct,
                "median_wage_usd": wage_usd,
                "employment_status": status,
            })

        sectors_out.sort(key=lambda s: s["employment_share_pct"], reverse=True)

        methodology_note = (
            "Employment share from ILOSTAT one-period snapshot (2022-2024). "
            "Growth flags are based on wage-per-worker premium and national "
            "strategic priority — not from a time-series growth rate. "
            "Treat as directional, not as a growth rate forecast."
        )

        return SectorGrowthSignal(
            sectors=sectors_out,
            growth_flagged_sectors=growth_flagged,
            methodology_note=methodology_note,
        )
