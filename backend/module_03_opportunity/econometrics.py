"""Module 03 — Econometric signals: wage floors and sector employment data.

No LLM calls. Two required econometric signals exposed to user.

All country-specific economic constants (ISCO→sector mapping, informal
discount factor, high-value wage threshold, strategic sectors) are loaded
from the country YAML config — see CountryConfig.labor_data fields.

Module-level _DEFAULT_* values exist only as a fallback when a country
YAML omits a field, to avoid crashing during incremental rollout.
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

# West Africa default ISCO 2-digit → sector label mapping. Used only when a
# country YAML omits labor_data.isco_to_sector_mapping. New countries with
# different ILOSTAT sector labels MUST provide their own mapping in YAML.
_DEFAULT_ISCO_TO_SECTOR: dict[str, str] = {
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

_DEFAULT_STRATEGIC_SECTORS: set[str] = {
    "Information and communication (ICT)",
    "Financial and insurance activities",
}


class EconometricSignals:
    """Surfaces two required econometric signals from ILOSTAT data.

    All economic constants are sourced from the country YAML config:
      - labor_data.isco_to_sector_mapping
      - labor_data.informal_sector_discount_factor
      - labor_data.high_value_wage_threshold_usd
      - labor_data.growth_strategic_sectors
    """

    def __init__(self, config: CountryConfig) -> None:
        """Load labor market data + country-specific economic constants."""
        self._config = config
        path = _BACKEND_DIR / config.labor_data.source_file
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._labor = LaborMarketData(**raw)

        # Wage lookup: sector → median_xof
        self._wage_by_sector: dict[str, int] = {
            w.sector: w.median_monthly_xof for w in self._labor.wage_by_sector
        }

        # Country-specific economic constants — fall back to West Africa defaults
        # when YAML omits them, but log so it's visible in production.
        ld = config.labor_data
        self._isco_to_sector = (
            ld.isco_to_sector_mapping if ld.isco_to_sector_mapping
            else _DEFAULT_ISCO_TO_SECTOR
        )
        self._informal_discount = ld.informal_sector_discount_factor
        self._high_value_threshold_usd = ld.high_value_wage_threshold_usd
        self._strategic_sectors = (
            set(ld.growth_strategic_sectors) if ld.growth_strategic_sectors
            else _DEFAULT_STRATEGIC_SECTORS
        )

        if not ld.isco_to_sector_mapping:
            logger.warning(
                "Country %s uses default West Africa ISCO mapping — "
                "supply labor_data.isco_to_sector_mapping in YAML for accuracy.",
                config.country_code,
            )

        logger.info(
            "EconometricSignals ready for %s: %d wage sectors, %d ISCO mappings, "
            "informal_discount=%.2f, strategic=%s",
            config.country_code,
            len(self._wage_by_sector),
            len(self._isco_to_sector),
            self._informal_discount,
            sorted(self._strategic_sectors),
        )

    # ------------------------------------------------------------------
    # Signal 1 — Wage
    # ------------------------------------------------------------------

    def get_wage_signals(self, profile: StandardizedProfile) -> WageSignal:
        """Estimate current income and formal wage gap (Signal 1)."""
        usd_rate = self._config.labor_data.usd_conversion_rate

        # Map profile ISCO groups to sectors (country-specific mapping)
        profile_isco = {
            code for skill in profile.skills for code in skill.isco_groups
        }
        profile_sectors = {
            self._isco_to_sector[code]
            for code in profile_isco
            if code in self._isco_to_sector
        }

        # Estimate current income: prefer informal trade sector wage if available;
        # otherwise apply country-specific informal discount to lowest matched sector.
        matched_wages = [
            self._wage_by_sector[s]
            for s in profile_sectors
            if s in self._wage_by_sector
        ]
        # Look up an informal-tagged sector dynamically (any sector containing "informal")
        informal_sector = next(
            (s for s in self._wage_by_sector if "informal" in s.lower()), None
        )
        if matched_wages and informal_sector:
            current_xof = self._wage_by_sector[informal_sector]
        elif matched_wages:
            current_xof = int(min(matched_wages) * self._informal_discount)
        else:
            # Fallback: agriculture wage (lowest) as conservative estimate
            agri_sector = next(
                (s for s in self._wage_by_sector if "Agriculture" in s), None
            )
            current_xof = self._wage_by_sector.get(agri_sector or "", 35000)

        current_usd = round(current_xof / usd_rate)

        # Formal median wages for profile-relevant sectors
        formal_by_sector = {
            s: self._wage_by_sector[s]
            for s in profile_sectors
            if s in self._wage_by_sector
        }
        # Include the strategic sector with highest wage as aspirational signal
        for strategic in self._strategic_sectors:
            if strategic in self._wage_by_sector:
                formal_by_sector[strategic] = self._wage_by_sector[strategic]

        best_formal_xof = max(formal_by_sector.values()) if formal_by_sector else current_xof
        gap_xof = best_formal_xof - current_xof
        multiplier = round(best_formal_xof / max(current_xof, 1), 2)

        methodology_note = (
            f"Current income estimated at informal sector median "
            f"({self._labor.country}, ILOSTAT {self._labor.year} reference). "
            f"Informal-to-formal discount factor: {self._informal_discount:.2f}. "
            f"Formal median wages from ILOSTAT sector survey data. "
            f"USD at {usd_rate} {self._config.labor_data.currency}/USD."
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
        usd_rate = self._config.labor_data.usd_conversion_rate
        sectors_out: list[dict] = []
        growth_flagged: list[str] = []

        for emp in self._labor.employment_by_sector:
            wage_info = self._wage_by_sector.get(emp.sector)
            wage_usd = round(wage_info / usd_rate) if wage_info else None

            # High-value classification by strategic OR by wage threshold
            is_high_value = (
                emp.sector in self._strategic_sectors
                or (wage_usd is not None and wage_usd >= self._high_value_threshold_usd)
            )

            if is_high_value:
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
            f"Employment share from ILOSTAT one-period snapshot ({self._labor.country}, "
            f"{self._labor.year}). High-value flag = wage ≥ ${self._high_value_threshold_usd}/mo "
            f"OR sector in country's strategic_sectors list "
            f"({sorted(self._strategic_sectors)}). "
            "Treat as directional, not as a growth rate forecast."
        )

        return SectorGrowthSignal(
            sectors=sectors_out,
            growth_flagged_sectors=sorted(set(growth_flagged)),
            methodology_note=methodology_note,
        )
