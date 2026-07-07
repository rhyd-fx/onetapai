from dataclasses import dataclass
from .aim_profiler import AimDeficiency, AimProfile

@dataclass
class PlayerHardwareProfile:
    mouse_dpi: int
    in_game_sens: float
    edpi: float
    
@dataclass
class DrillPrescription:
    drill_name: str
    platform: str              # "aim_lab" | "kovaaks"
    duration_minutes: int
    focus: str
    settings: dict[str, str | float]

def prescribe_drills(
    profile: AimProfile,
    hardware: PlayerHardwareProfile,
) -> list[DrillPrescription]:
    """
    Generate hardware-aware aim training prescriptions.

    Key insight: A 1600 DPI player needs different drills than a 400 DPI player.
    High eDPI → focus on micro-adjustment precision (small targets, slow tracking).
    Low eDPI → focus on large flick consistency (arm aim, 180° scenarios).
    """
    drills = []
    edpi = hardware.edpi  # DPI × in-game sensitivity

    if AimDeficiency.CROSSHAIR_TOO_LOW in profile.deficiencies:
        # Crosshair placement is a HABIT, not a flick skill
        drills.append(DrillPrescription(
            drill_name="Headshot Level Tracking" if edpi > 400 else "Centering Practice",
            platform="aim_lab",
            duration_minutes=10,
            focus="Hold crosshair at head level while strafing through map geometry",
            settings={
                "sensitivity": hardware.in_game_sens,
                "dpi": hardware.mouse_dpi,
                "target_size": "small" if edpi > 400 else "medium",
                "scenario": (
                    "Valorant Plaza Head Level"
                    if edpi > 400
                    else "Valorant Ascent Mid Crosshair Drill"
                ),
            },
        ))

    if AimDeficiency.MOVING_WHILE_SHOOTING in profile.deficiencies:
        drills.append(DrillPrescription(
            drill_name="Counter-Strafe Discipline",
            platform="kovaaks",
            duration_minutes=15,
            focus=(
                "Practice ADAD counter-strafing with first-bullet accuracy. "
                "Zero your velocity before every shot."
            ),
            settings={
                "sensitivity": hardware.in_game_sens,
                "dpi": hardware.mouse_dpi,
                "scenario": "1w4ts Valorant",
                "note": (
                    f"At {edpi:.0f} eDPI, focus on "
                    + ("wrist micro-adjustments between strafes"
                       if edpi > 400
                       else "arm resets between strafes")
                ),
            },
        ))

    if AimDeficiency.OVER_FLICKING in profile.deficiencies:
        target_size = "tiny" if edpi > 600 else "small" if edpi > 300 else "medium"
        drills.append(DrillPrescription(
            drill_name="Long-Range Precision Flicks",
            platform="aim_lab",
            duration_minutes=12,
            focus="Reduce over-flicking on distant targets",
            settings={
                "sensitivity": hardware.in_game_sens,
                "dpi": hardware.mouse_dpi,
                "target_size": target_size,
                "scenario": "Sixshot Ultimate",
                "note": (
                    f"Your eDPI ({edpi:.0f}) suggests you "
                    + ("overshoot on micro-adjustments — slow down your wrist"
                       if edpi > 400
                       else "need larger arm movements — commit to the flick")
                ),
            },
        ))

    return drills
