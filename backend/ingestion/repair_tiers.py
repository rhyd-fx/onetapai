"""One-time repair: restore true competitive tiers from the raw match archive.

An earlier ETL version stored a per-match scoreboard ranking in
player_match_stats.tier_id instead of the player's actual rank — in the
affected matches the highest-ACS player always got the highest tier, and
lobbies span an impossible 15 tier steps (Bronze 1 → Ascendant 1). The
archived Henrik payloads carry the correct `currenttier`, so the fix is a
targeted UPDATE rather than a re-ingest: only these two columns are wrong.

Usage (from backend/):  python -m ingestion.repair_tiers [--dry-run] [--limit N]
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config  # noqa: F401  (loads .env)

from ingestion.etl import get_db_connection

RAW_DIR = os.path.join(str(config.REPO_ROOT), "data", "raw")


def _raw_tiers(path: str) -> dict[str, tuple[int, str]]:
    """puuid -> (currenttier, currenttier_patched) from an archived payload."""
    with open(path) as f:
        match = json.load(f)
    players = match.get("players") or {}
    if isinstance(players, dict):
        players = players.get("all_players") or []
    out = {}
    for p in players:
        puuid = p.get("puuid")
        tier = p.get("currenttier")
        if puuid and tier is not None:
            out[puuid] = (int(tier), p.get("currenttier_patched") or "Unrated")
    return out


def main() -> None:
    dry = "--dry-run" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT match_id FROM player_match_stats")
        match_ids = [r["match_id"] for r in cur.fetchall()]
    if limit:
        match_ids = match_ids[:limit]

    print(f"{len(match_ids)} matches in DB; archive at {RAW_DIR}")
    no_archive = unchanged = 0
    rows_fixed = matches_fixed = 0
    failed = 0

    for mid in match_ids:
        path = os.path.join(RAW_DIR, f"{mid}_henrik.json")
        if not os.path.exists(path):
            no_archive += 1
            continue
        try:
            truth = _raw_tiers(path)
            if not truth:
                unchanged += 1
                continue

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT puuid, tier_id, tier_name FROM player_match_stats WHERE match_id = %s",
                    (mid,),
                )
                current = cur.fetchall()

            updates = [
                (t[0], t[1], mid, r["puuid"])
                for r in current
                if (t := truth.get(r["puuid"])) is not None
                and (int(r["tier_id"] or 0) != t[0] or (r["tier_name"] or "") != t[1])
            ]
            if not updates:
                unchanged += 1
                continue

            matches_fixed += 1
            rows_fixed += len(updates)
            if not dry:
                with conn.cursor() as cur:
                    cur.executemany(
                        "UPDATE player_match_stats SET tier_id = %s, tier_name = %s "
                        "WHERE match_id = %s AND puuid = %s",
                        updates,
                    )
                conn.commit()
        except Exception as e:  # noqa: BLE001 — keep going, report at the end
            failed += 1
            print(f"  ! {mid}: {e}")

    conn.close()
    print(
        f"Done. matches_repaired={matches_fixed} rows_repaired={rows_fixed} "
        f"already_correct={unchanged} no_archive={no_archive} failed={failed}"
        + (" [DRY RUN — nothing written]" if dry else "")
    )


if __name__ == "__main__":
    main()
