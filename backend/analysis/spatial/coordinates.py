"""Unreal-world → normalized UI coordinate mapping for Valorant maps.

Henrik/Riot report kill and player positions in raw Unreal world units — large
signed values whose range differs per map (e.g. Split spans x∈[-3.5k, 8.1k],
y∈[-9k, -1k], with Y entirely negative). To plot them on a fixed minimap image
we normalize to [0, 1] (or 0–100%) using per-map bounding boxes.

IMPORTANT: bounds are the robust **1st–99th percentile** of observed
coordinates, NOT raw min/max. The ingested data contains sentinel (0,0) points
(from failed location lookups) and out-of-bounds outliers (e.g. x=-51237) that
would otherwise blow the bounding box wide open and squash every real point into
a tiny sub-range.

Only 'Split' is calibrated from real ingested data so far. Every other map falls
back to a generous placeholder envelope (points stay on-canvas via clamping, but
are NOT visually accurate). Calibrate a map from ingested data with the CLI:

    python -m analysis.spatial.coordinates Ascent      # prints derived bounds
"""
from __future__ import annotations

# --- Per-map bounding boxes (raw Unreal world units) ---

# Data-derived: p1–p99 of ingested Split kill_events, padded ~2% for headroom.
_SPLIT = {"x_min": -3500.0, "x_max": 8100.0, "y_min": -9050.0, "y_max": -1050.0}

# Generous placeholder envelope for uncalibrated maps. Chosen to cover the
# observed extent across maps so clamping keeps points on-canvas.
DEFAULT_BOUNDS = {"x_min": -9500.0, "x_max": 16100.0, "y_min": -13900.0, "y_max": 12600.0}

# Current competitive + non-competitive map pool. Uncalibrated entries point at
# DEFAULT_BOUNDS and MUST be calibrated per map via the CLI as data lands.
MAP_BOUNDS: dict[str, dict] = {
    "Split": _SPLIT,
    "Ascent": DEFAULT_BOUNDS,    # PLACEHOLDER — calibrate
    "Bind": DEFAULT_BOUNDS,      # PLACEHOLDER — calibrate
    "Haven": DEFAULT_BOUNDS,     # PLACEHOLDER — calibrate
    "Breeze": DEFAULT_BOUNDS,    # PLACEHOLDER — calibrate
    "Fracture": DEFAULT_BOUNDS,  # PLACEHOLDER — calibrate
    "Icebox": DEFAULT_BOUNDS,    # PLACEHOLDER — calibrate
    "Lotus": DEFAULT_BOUNDS,     # PLACEHOLDER — calibrate
    "Pearl": DEFAULT_BOUNDS,     # PLACEHOLDER — calibrate
    "Sunset": DEFAULT_BOUNDS,    # PLACEHOLDER — calibrate
    "Abyss": DEFAULT_BOUNDS,     # PLACEHOLDER — calibrate
    "Corrode": DEFAULT_BOUNDS,   # PLACEHOLDER — calibrate
}


# --- Official Riot minimap calibration (from valorant-api.com) ---
# Per map: (xMultiplier, yMultiplier, xScalarToAdd, yScalarToAdd, uuid).
# Riot's transform maps a game (x, y) to a 0..1 fraction of the minimap image:
#   frac_x = game_y * xMultiplier + xScalarToAdd
#   frac_y = game_x * yMultiplier + yScalarToAdd
# (note the x/y swap). This aligns dots to the real minimap displayIcon.
MAP_CALIBRATION: dict[str, tuple] = {
    "Ascent":  (7.0e-05, -7.0e-05, 0.813895, 0.573242, "7eaecc1b-4337-bbf6-6ab9-04b8f06b3319"),
    "Split":   (7.8e-05, -7.8e-05, 0.842188, 0.697578, "d960549e-485c-e861-8d71-aa9d1aed12a2"),
    "Fracture":(7.8e-05, -7.8e-05, 0.556952, 1.155886, "b529448b-4d60-346e-e89e-00a4c527a405"),
    "Bind":    (5.9e-05, -5.9e-05, 0.576941, 0.967566, "2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba"),
    "Breeze":  (7.0e-05, -7.0e-05, 0.465123, 0.833078, "2fb9a4fd-47b8-4e7d-a969-74b4046ebd53"),
    "Abyss":   (8.1e-05, -8.1e-05, 0.5, 0.5, "224b0a95-48b9-f703-1bd8-67aca101a61f"),
    "Lotus":   (7.2e-05, -7.2e-05, 0.454789, 0.917752, "2fe4ed3a-450a-948b-6d6b-e89a78e680a9"),
    "Sunset":  (7.8e-05, -7.8e-05, 0.5, 0.515625, "92584fbe-486a-b1b2-9faa-39b0f486b498"),
    "Pearl":   (7.8e-05, -7.8e-05, 0.480469, 0.916016, "fd267378-4d1d-484f-ff52-77821ed10dc2"),
    "Summit":  (7.5e-05, -7.5e-05, 0.047401, 0.978891, "756da597-416b-c0f2-f47b-afbdf28670bc"),
    "Icebox":  (7.2e-05, -7.2e-05, 0.460214, 0.304687, "e2ad5c54-4114-a870-9641-8ea21279579a"),
    "Corrode": (7.0e-05, -7.0e-05, 0.526158, 0.5, "1c18ab1f-420d-0d8b-71d0-77ad3c439115"),
    "Haven":   (7.5e-05, -7.5e-05, 1.09345, 0.642728, "2bee0dc9-4ffe-519b-1cbd-7fbe763a6047"),
}


def has_official_calibration(map_id: str) -> bool:
    return map_id in MAP_CALIBRATION


def minimap_url(map_id: str) -> str | None:
    c = MAP_CALIBRATION.get(map_id)
    return f"https://media.valorant-api.com/maps/{c[4]}/displayicon.png" if c else None


def official_to_percent(map_id: str, x: float, y: float) -> tuple[float, float] | None:
    """Game (x, y) → (left%, top%) on the real minimap via Riot's transform."""
    c = MAP_CALIBRATION.get(map_id)
    if not c:
        return None
    x_mult, y_mult, x_add, y_add, _ = c
    fx = _clamp01(y * x_mult + x_add)
    fy = _clamp01(x * y_mult + y_add)
    return round(fx * 100, 2), round(fy * 100, 2)


def get_bounds(map_id: str) -> dict:
    """Bounding box for a map, or the placeholder envelope if unknown."""
    return MAP_BOUNDS.get(map_id, DEFAULT_BOUNDS)


def is_calibrated(map_id: str) -> bool:
    """True if the map has real (non-placeholder) bounds."""
    b = MAP_BOUNDS.get(map_id)
    return b is not None and b is not DEFAULT_BOUNDS


def map_span(map_id: str) -> float:
    """Largest axis extent of the map, in world units (used to scale thresholds)."""
    b = get_bounds(map_id)
    return max(b["x_max"] - b["x_min"], b["y_max"] - b["y_min"])


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def normalize(map_id: str, x: float, y: float, invert_y: bool = True) -> tuple[float, float]:
    """Raw Unreal (x, y) → normalized (nx, ny) in [0, 1], clamped on-canvas.

    `invert_y` flips the vertical axis into image space (where y grows downward),
    so a point at the top of the world renders at the top of the image.
    """
    b = get_bounds(map_id)
    xr = (b["x_max"] - b["x_min"]) or 1.0
    yr = (b["y_max"] - b["y_min"]) or 1.0
    nx = _clamp01((x - b["x_min"]) / xr)
    ny = _clamp01((y - b["y_min"]) / yr)
    if invert_y:
        ny = 1.0 - ny
    return nx, ny


def to_percent(map_id: str, x: float, y: float, invert_y: bool = True) -> tuple[float, float]:
    """Same as `normalize` but returns 0–100 percentages for CSS positioning."""
    nx, ny = normalize(map_id, x, y, invert_y)
    return round(nx * 100, 2), round(ny * 100, 2)


def to_percent_with(bounds: dict, x: float, y: float, invert_y: bool = True) -> tuple[float, float]:
    """Normalize to 0–100% using an explicit bounds dict (e.g. one derived live
    from the ingested data for a specific map)."""
    xr = (bounds["x_max"] - bounds["x_min"]) or 1.0
    yr = (bounds["y_max"] - bounds["y_min"]) or 1.0
    nx = _clamp01((x - bounds["x_min"]) / xr)
    ny = _clamp01((y - bounds["y_min"]) / yr)
    if invert_y:
        ny = 1.0 - ny
    return round(nx * 100, 2), round(ny * 100, 2)


def derive_bounds(points, lo: float = 1.0, hi: float = 99.0) -> dict:
    """Robust p[lo]–p[hi] bounds from an iterable of (x, y) coordinate pairs.

    Drops exact (0,0) sentinels and uses percentiles so out-of-bounds outliers
    don't wreck the box. Returns a MAP_BOUNDS-shaped dict.
    """
    import numpy as np

    arr = np.asarray([(float(px), float(py)) for px, py in points], dtype=float)
    if len(arr) == 0:
        return dict(DEFAULT_BOUNDS)
    mask = ~((arr[:, 0] == 0) & (arr[:, 1] == 0))
    arr = arr[mask]
    xs, ys = arr[:, 0], arr[:, 1]
    return {
        "x_min": float(np.percentile(xs, lo)),
        "x_max": float(np.percentile(xs, hi)),
        "y_min": float(np.percentile(ys, lo)),
        "y_max": float(np.percentile(ys, hi)),
    }


def _cli() -> None:
    """Calibration helper: derive bounds for a map from the ingested DB.

    Usage: python -m analysis.spatial.coordinates <MapName>
    """
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from ingestion.etl import get_db_connection  # noqa: E402

    if len(sys.argv) < 2:
        print("Usage: python -m analysis.spatial.coordinates <MapName>")
        return
    map_id = sys.argv[1]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ke.killer_x AS kx, ke.killer_y AS ky,
                       ke.victim_x AS vx, ke.victim_y AS vy
                FROM kill_events ke
                JOIN rounds r ON ke.round_id = r.id
                JOIN matches m ON r.match_id = m.match_id
                WHERE m.map_id = %s
                """,
                (map_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    pts = [(r["kx"], r["ky"]) for r in rows] + [(r["vx"], r["vy"]) for r in rows]
    if not pts:
        print(f"No kill_events for map {map_id!r} — ingest matches on that map first.")
        return
    bounds = derive_bounds(pts)
    print(f"# Derived from {len(pts)} points ({map_id}). Paste into MAP_BOUNDS:")
    print(f'    "{map_id}": {{'
          f'"x_min": {bounds["x_min"]:.0f}, "x_max": {bounds["x_max"]:.0f}, '
          f'"y_min": {bounds["y_min"]:.0f}, "y_max": {bounds["y_max"]:.0f}}},')


if __name__ == "__main__":
    _cli()
