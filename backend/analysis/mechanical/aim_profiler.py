from dataclasses import dataclass
from enum import StrEnum

class AimDeficiency(StrEnum):
    CROSSHAIR_TOO_LOW = "crosshair_too_low"       # High bodyshot %, few headshots
    CROSSHAIR_TOO_HIGH = "crosshair_too_high"      # High legshot % (rare)
    OVER_FLICKING = "over_flicking"                # Inconsistent headshot % at range
    UNDER_TRACKING = "under_tracking"              # Bodyshots increase with engagement time
    SPRAY_TRANSFER_WEAK = "spray_transfer_weak"    # Multi-kill bodyshot % >> single-kill
    MOVING_WHILE_SHOOTING = "moving_while_shooting" # Deaths with 0 damage dealt

@dataclass
class AimProfile:
    headshot_pct: float
    bodyshot_pct: float
    legshot_pct: float
    headshot_pct_by_range: dict[str, float]  # "short" | "medium" | "long"
    bodyshot_pct_eco_vs_full: dict[str, float]  # "eco" | "full_buy"
    opening_duel_hs_pct: float
    zero_damage_death_pct: float  # Died without dealing any damage
    deficiencies: list[AimDeficiency]

    @classmethod
    def from_db_stats(cls, stats: dict) -> "AimProfile":
        deficiencies = []

        # Crosshair placement detection
        if stats["bodyshot_pct"] > 0.55 and stats["headshot_pct"] < 0.20:
            deficiencies.append(AimDeficiency.CROSSHAIR_TOO_LOW)

        # Moving-while-shooting detection
        if stats["zero_damage_death_pct"] > 0.25:
            deficiencies.append(AimDeficiency.MOVING_WHILE_SHOOTING)

        # Range-dependent accuracy degradation
        if (stats["hs_by_range"].get("long", 0) < stats["hs_by_range"].get("short", 1) * 0.5):
            deficiencies.append(AimDeficiency.OVER_FLICKING)

        return cls(
            headshot_pct=stats["headshot_pct"],
            bodyshot_pct=stats["bodyshot_pct"],
            legshot_pct=stats["legshot_pct"],
            headshot_pct_by_range=stats["hs_by_range"],
            bodyshot_pct_eco_vs_full=stats["bs_by_econ"],
            opening_duel_hs_pct=stats["opening_hs_pct"],
            zero_damage_death_pct=stats["zero_damage_death_pct"],
            deficiencies=deficiencies,
        )
