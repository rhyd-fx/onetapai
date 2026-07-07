"""One-time repair: re-ingest matches whose team ids were stored as raw UUIDs
(premier/custom matches) before the team-normalization fix.

For each affected match with archived raw JSON, delete its rows and re-process
through the (now fixed) ETL so team_id/winning_team become canonical Red/Blue
and `won` is recomputed from round-win counts.

Usage (from backend/):  python -m ingestion.repair_teams [--dry-run]
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config  # noqa: F401  (loads .env)
import json

from ingestion.etl import get_db_connection, process_match

RAW_DIR = os.path.join(str(config.REPO_ROOT), "data", "raw")


def _delete_match(conn, match_id: str) -> None:
    """Remove all rows for a match so it can be cleanly re-ingested."""
    with conn.cursor() as cur:
        # Child rows first (FKs). kill_events/player_round_stats/player_locations
        # hang off rounds; player_match_stats off matches.
        cur.execute(
            """DELETE ke FROM kill_events ke
               JOIN rounds r ON ke.round_id = r.id WHERE r.match_id = %s""",
            (match_id,),
        )
        cur.execute(
            """DELETE prs FROM player_round_stats prs
               JOIN rounds r ON prs.round_id = r.id WHERE r.match_id = %s""",
            (match_id,),
        )
        cur.execute(
            """DELETE pl FROM player_locations pl
               JOIN rounds r ON pl.round_id = r.id WHERE r.match_id = %s""",
            (match_id,),
        )
        cur.execute("DELETE FROM rounds WHERE match_id = %s", (match_id,))
        cur.execute("DELETE FROM player_match_stats WHERE match_id = %s", (match_id,))
        cur.execute("DELETE FROM matches WHERE match_id = %s", (match_id,))
    conn.commit()


def main() -> None:
    dry = "--dry-run" in sys.argv
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT match_id FROM player_match_stats "
            "WHERE team_id NOT IN ('Red','Blue')"
        )
        bad = [r["match_id"] for r in cur.fetchall()]

    print(f"{len(bad)} matches need repair.")
    fixed = skipped = failed = 0
    for mid in bad:
        path = os.path.join(RAW_DIR, f"{mid}_henrik.json")
        if not os.path.exists(path):
            skipped += 1
            continue
        if dry:
            fixed += 1
            continue
        try:
            with open(path) as f:
                match = json.load(f)
            _delete_match(conn, mid)
            process_match(match, conn)
            fixed += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ! {mid}: {e}")
    conn.close()
    print(f"Done. repaired={fixed} skipped(no JSON)={skipped} failed={failed}"
          + (" [DRY RUN]" if dry else ""))


if __name__ == "__main__":
    main()
