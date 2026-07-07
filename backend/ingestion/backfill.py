"""Batch backfill: snowball-crawl Henrik matches from seed players into MariaDB.

Starts from a seed set of Riot IDs, fetches each player's recent full matches,
archives the raw JSON (local + optional S3/MinIO), runs the ETL into MariaDB,
and harvests the 10 players from each match to discover more players — repeating
(breadth-first) until TARGET new matches are ingested or the frontier empties.

Usage:
    python backfill.py                                  # seeds/target from config/.env
    python backfill.py --target 1000 --size 10 Friday#PlayZ TenZ#0505
    python backfill.py --region eu ScreaM#EU

Requires HENRIK_API_KEY and a reachable MariaDB (docker compose up).
"""
import argparse
import asyncio
import os
import sys
from collections import deque

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

import archiver
from etl import get_db_connection, process_match
from worker import HenrikAPIClient

# Fallback seed if none supplied. Replace with well-known active accounts.
DEFAULT_SEEDS = [("Friday", "PlayZ", "ap")]


def _load_seen_match_ids(conn) -> set[str]:
    """Existing match_ids in the DB, so a re-run resumes instead of re-ingesting."""
    with conn.cursor() as cur:
        cur.execute("SELECT match_id FROM matches")
        return {row["match_id"] for row in cur.fetchall()}


async def backfill(seeds, target: int, size: int, region_default: str) -> int:
    client = HenrikAPIClient.from_config()
    conn = get_db_connection()
    seen = _load_seen_match_ids(conn)
    visited_players: set[tuple[str, str]] = set()
    frontier = deque(seeds)
    ingested = 0

    print(
        f"Backfill start: target={target} new matches, "
        f"{len(seen)} already in DB, {len(seeds)} seed player(s)."
    )
    try:
        while frontier and ingested < target:
            name, tag, region = frontier.popleft()
            pkey = (name.lower(), tag.lower())
            if pkey in visited_players:
                continue
            visited_players.add(pkey)

            try:
                matches = await client.get_matches(
                    region or region_default, name, tag, size=size
                )
            except Exception as e:  # noqa: BLE001 — skip a bad player, keep crawling
                print(f"  ! fetch failed for {name}#{tag}: {e}")
                continue

            new_here = 0
            for match in matches:
                meta = match.get("metadata", {})
                if not meta:
                    print(f"  ! Warning: Match object missing metadata field. Skipping.")
                    continue
                mid = meta.get("matchid")
                if not mid or mid in seen:
                    continue

                archiver.archive_match(mid, match)
                try:
                    process_match(match, conn)  # commits on success, rolls back on error
                except Exception as e:  # noqa: BLE001
                    print(f"    ! ETL failed for {mid}: {e}")
                    continue

                seen.add(mid)
                ingested += 1
                new_here += 1

                # Snowball: enqueue every player in this match for discovery.
                for p in match.get("players", {}).get("all_players", []):
                    pn, pt = p.get("name"), p.get("tag")
                    if pn and pt and (pn.lower(), pt.lower()) not in visited_players:
                        frontier.append((pn, pt, meta.get("region") or region_default))

                if ingested >= target:
                    break

            print(
                f"[{ingested}/{target}] {name}#{tag}: +{new_here} new "
                f"(frontier={len(frontier)})"
            )

        if not frontier and ingested < target:
            print(
                "Frontier exhausted before reaching target — add more/broader "
                "seed players or increase --size."
            )
        print(f"Done. Ingested {ingested} new matches ({len(seen)} total in DB).")
        return ingested
    finally:
        await client.close()
        conn.close()


def _parse_seeds(riot_ids: list[str], region: str):
    seeds = []
    for rid in riot_ids:
        if "#" in rid:
            name, tag = rid.rsplit("#", 1)
            seeds.append((name.strip(), tag.strip(), region))
        else:
            print(f"  ! ignoring malformed Riot ID (expected Name#Tag): {rid!r}")
    return seeds


def main():
    ap = argparse.ArgumentParser(description="Snowball-backfill Henrik matches into MariaDB.")
    ap.add_argument("--target", type=int, default=config.BACKFILL_TARGET,
                    help="number of new matches to ingest")
    ap.add_argument("--size", type=int, default=config.BACKFILL_SIZE,
                    help="matches requested per player")
    ap.add_argument("--region", default="na",
                    help="default region for seeds without a known region")
    ap.add_argument("players", nargs="*", help="seed Riot IDs, e.g. Name#Tag")
    args = ap.parse_args()

    seeds = _parse_seeds(args.players, args.region) or DEFAULT_SEEDS
    asyncio.run(backfill(seeds, args.target, args.size, args.region))


if __name__ == "__main__":
    main()
