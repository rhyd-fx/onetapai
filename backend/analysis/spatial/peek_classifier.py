import numpy as np
from enum import StrEnum
from dataclasses import dataclass

# Map-scaled threshold calibration. Thresholds are expressed as a fraction of
# the map's world-unit span so a "tight peek" means the same thing on a small
# map as on a large one. Absolute defaults below are these fractions applied to
# the reference map (Split, ~11,600-unit span).
REFERENCE_SPAN = 11600.0
_TIGHT_FRAC = 0.02       # TIGHT_PEEK: died within ~2% of map span of a wall
_WIDE_FRAC = 0.05        # WIDE_SWING: died >~5% of map span from any wall
_CROSSFIRE_FRAC = 0.03   # CROSSFIRE_ENTRY: died within ~3% of a crossfire zone


class PeekType(StrEnum):
    WIDE_SWING = "wide_swing"          # Exposed to multiple angles
    TIGHT_PEEK = "tight_peek"          # Close to wall geometry
    JIGGLE_PEEK = "jiggle_peek"        # Minimal exposure (inferred from survival)
    CROSSFIRE_ENTRY = "crossfire_entry" # Died in a multi-angle kill zone
    OFF_ANGLE = "off_angle"            # Unconventional position
    UNKNOWN = "unknown"

@dataclass
class MapGeometry:
    """Pre-computed wall segments and common angle points for a map."""
    wall_segments: np.ndarray   # Shape: (N, 2, 2) — N segments, each [(x1,y1), (x2,y2)]
    choke_points: np.ndarray    # Shape: (M, 2) — known crossfire zones
    common_angles: np.ndarray   # Shape: (K, 2) — common hold positions

    def distance_to_nearest_wall(self, point: np.ndarray) -> float:
        """Minimum perpendicular distance from point to any wall segment.

        Returns +inf when the map has no wall segments, so distance-based
        thresholds simply never fire instead of raising on np.min([]).
        """
        if len(self.wall_segments) == 0:
            return float("inf")
        # Vector math: project point onto each segment, clamp, measure distance
        p1 = self.wall_segments[:, 0, :]  # (N, 2)
        p2 = self.wall_segments[:, 1, :]  # (N, 2)
        d = p2 - p1
        # Parameter t along each segment
        t = np.sum((point - p1) * d, axis=1) / (np.sum(d * d, axis=1) + 1e-10)
        t = np.clip(t, 0.0, 1.0)
        projections = p1 + t[:, np.newaxis] * d
        distances = np.linalg.norm(projections - point, axis=1)
        return float(np.min(distances))

    def is_in_crossfire_zone(
        self, point: np.ndarray, threshold: float = 50.0
    ) -> bool:
        """Check if point is within threshold distance of a known crossfire zone."""
        if len(self.choke_points) == 0:
            return False
        distances = np.linalg.norm(self.choke_points - point, axis=1)
        return bool(np.min(distances) < threshold)


def classify_peek(
    death_pos: np.ndarray,         # (x, y) where player died
    killer_pos: np.ndarray,        # (x, y) where killer was
    map_geo: MapGeometry,
    # Thresholds are in RAW UNREAL WORLD UNITS (a map spans ~11,600 units), NOT a
    # 0-1024 grid. Defaults are calibrated for the reference map (Split). For
    # correct per-map scaling, prefer classify_peek_for_map(), which derives
    # these from the map's true span.
    wall_proximity_threshold: float = _TIGHT_FRAC * REFERENCE_SPAN,   # ~232 u ("close to a wall")
    wide_swing_threshold: float = _WIDE_FRAC * REFERENCE_SPAN,        # ~580 u (far from any wall)
    crossfire_threshold: float = _CROSSFIRE_FRAC * REFERENCE_SPAN,    # ~348 u (near a crossfire zone)
    off_angle_rad_threshold: float = 0.5,                            # radians (~28.6°)
) -> PeekType:
    """
    Classify the peek type based on death position geometry.

    Coordinates are raw Unreal world units (large signed values), matching
    what the ETL stores in kill_events. Do not assume a normalized 0-1024 space.

    Heuristics:
    1. If death_pos is in a crossfire zone → CROSSFIRE_ENTRY
    2. If death_pos is close to a wall → TIGHT_PEEK
    3. If death_pos is far from walls → WIDE_SWING
    4. If the engagement came from an unexpected angle → OFF_ANGLE
    """
    wall_dist = map_geo.distance_to_nearest_wall(death_pos)
    in_crossfire = map_geo.is_in_crossfire_zone(death_pos, crossfire_threshold)

    # Engagement vector analysis
    engagement_vec = killer_pos - death_pos
    engagement_angle = np.arctan2(engagement_vec[1], engagement_vec[0])

    # Check against common hold angles at this position
    if len(map_geo.common_angles) > 0:
        hold_angles = np.arctan2(
            map_geo.common_angles[:, 1] - death_pos[1],
            map_geo.common_angles[:, 0] - death_pos[0],
        )
        # Normalize each angular difference to (-pi, pi] before taking abs, so
        # e.g. +3.0 rad vs -3.0 rad reads as ~0.28 apart (not ~6.0) — otherwise
        # any angle straddling the ±pi wrap is falsely flagged OFF_ANGLE.
        raw_diff = hold_angles - engagement_angle
        wrapped_diff = np.arctan2(np.sin(raw_diff), np.cos(raw_diff))
        min_angle_diff = float(np.min(np.abs(wrapped_diff)))
    else:
        min_angle_diff = 0.0

    # Classification logic
    if in_crossfire:
        return PeekType.CROSSFIRE_ENTRY
    elif wall_dist < wall_proximity_threshold:
        return PeekType.TIGHT_PEEK
    elif wall_dist > wide_swing_threshold:
        return PeekType.WIDE_SWING
    elif min_angle_diff > off_angle_rad_threshold:
        return PeekType.OFF_ANGLE
    else:
        return PeekType.UNKNOWN


def thresholds_for_map(map_id: str) -> dict:
    """World-unit thresholds scaled to a specific map's span.

    Uses the calibrated per-map bounds in analysis.spatial.coordinates so the
    same fractional definition of tight/wide holds across differently-sized maps.
    """
    try:
        from analysis.spatial import coordinates
    except ImportError:  # when run with spatial/ directly on sys.path
        import coordinates
    span = coordinates.map_span(map_id)
    return {
        "wall_proximity_threshold": _TIGHT_FRAC * span,
        "wide_swing_threshold": _WIDE_FRAC * span,
        "crossfire_threshold": _CROSSFIRE_FRAC * span,
    }


def classify_peek_for_map(
    map_id: str,
    death_pos: np.ndarray,
    killer_pos: np.ndarray,
    map_geo: MapGeometry,
    off_angle_rad_threshold: float = 0.5,
) -> PeekType:
    """Classify a peek using thresholds calibrated to `map_id`'s true world span."""
    t = thresholds_for_map(map_id)
    return classify_peek(
        death_pos,
        killer_pos,
        map_geo,
        wall_proximity_threshold=t["wall_proximity_threshold"],
        wide_swing_threshold=t["wide_swing_threshold"],
        crossfire_threshold=t["crossfire_threshold"],
        off_angle_rad_threshold=off_angle_rad_threshold,
    )
