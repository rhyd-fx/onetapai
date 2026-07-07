"""
ETL Pipeline for Henrik Dev API v3 → MariaDB

Processes raw Henrik API match JSON into normalized relational tables:
- matches, players, player_match_stats
- rounds (with plant/defuse data)
- kill_events (with correct round mapping, killer location, opening kill detection)
- player_round_stats (per-round economy, damage, hit distribution)
- player_locations (from kill event snapshots)
"""

import json
import os
import sys

import pymysql
from collections import defaultdict

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config


def get_db_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _find_killer_location(kill: dict) -> tuple[float, float]:
    """
    Find the killer's X/Y from player_locations_on_kill by matching puuid.
    
    Henrik API stores ALL player locations at the moment of each kill.
    We must find the specific entry matching the killer's puuid.
    """
    killer_puuid = kill.get("killer_puuid", "")
    for loc in kill.get("player_locations_on_kill", []):
        if loc.get("player_puuid") == killer_puuid:
            location = loc.get("location", {})
            return (location.get("x", 0), location.get("y", 0))
    return (0, 0)


def _determine_finishing_damage_type(round_data: dict, killer_puuid: str, victim_puuid: str) -> str:
    """
    Infer finishing damage type from round-level damage_events.
    
    Henrik kills don't include headshot/bodyshot/legshot directly.
    We look at the killer's damage_events for the victim in this round
    and pick the dominant hit type.
    """
    for ps in round_data.get("player_stats", []):
        if ps.get("player_puuid") != killer_puuid:
            continue
        for dmg in ps.get("damage_events", []):
            if dmg.get("receiver_puuid") != victim_puuid:
                continue
            hs = dmg.get("headshots", 0)
            bs = dmg.get("bodyshots", 0)
            ls = dmg.get("legshots", 0)
            # The finishing blow type is approximated by the dominant hit type
            if hs >= bs and hs >= ls and hs > 0:
                return "headshot"
            elif ls > bs and ls > hs and ls > 0:
                return "legshot"
            elif bs > 0 or (hs == 0 and ls == 0):
                return "bodyshot"
    return "unknown"


def _build_player_agent_map(players: list[dict]) -> dict[str, str]:
    """Build a puuid → character (agent) mapping from the players array."""
    return {p["puuid"]: p.get("character", "Unknown") for p in players}


def _build_player_team_map(players: list[dict]) -> dict[str, str]:
    """Build a puuid → team mapping from the players array."""
    return {p["puuid"]: p.get("team", "Unknown") for p in players}


def _compute_hit_percentages(stats: dict) -> tuple[float | None, float | None, float | None]:
    """
    Compute headshot/bodyshot/legshot percentages from Henrik player stats.
    
    Henrik provides raw hit counts: stats.headshots, stats.bodyshots, stats.legshots
    """
    hs = stats.get("headshots", 0)
    bs = stats.get("bodyshots", 0)
    ls = stats.get("legshots", 0)
    total = hs + bs + ls
    if total == 0:
        return (None, None, None)
    return (
        round(hs / total, 4),
        round(bs / total, 4),
        round(ls / total, 4),
    )


def _build_team_normalizer(match: dict) -> tuple[dict, str]:
    """Normalize team identity to canonical 'Red'/'Blue' and find the winner.

    Henrik uses 'Red'/'Blue' for standard matches but arbitrary team UUIDs for
    premier/custom matches (where teams.*.has_won is null). To store one
    consistent scheme, map every raw team id → 'Red'/'Blue' and determine the
    winner from round-win counts (works for all match types).

    Returns (raw_team_id -> 'Red'/'Blue', winning_canonical_team).
    """
    players = match.get("players", {}).get("all_players", [])
    rounds_data = match.get("rounds", [])

    # Distinct raw team ids, in first-seen order for deterministic mapping.
    raw_ids: list[str] = []
    for p in players:
        t = p.get("team")
        if t and t not in raw_ids:
            raw_ids.append(t)

    # If already Red/Blue, keep that mapping; otherwise assign by first-seen.
    canon: dict[str, str] = {}
    if set(raw_ids) <= {"Red", "Blue"}:
        canon = {t: t for t in raw_ids}
    else:
        for i, t in enumerate(raw_ids):
            canon[t] = "Red" if i == 0 else "Blue"

    # Winner = team with the most round wins (robust across match types).
    wins: dict[str, int] = {}
    for r in rounds_data:
        wt = r.get("winning_team")
        if wt is not None:
            wins[wt] = wins.get(wt, 0) + 1
    winning_raw = max(wins, key=wins.get) if wins else None

    # Fallback to teams.has_won when round data is unavailable.
    if winning_raw is None:
        teams = match.get("teams", {})
        for key in ("red", "blue"):
            if (teams.get(key) or {}).get("has_won"):
                winning_raw = key.capitalize()
                break

    winning_team = canon.get(winning_raw, "Red") if winning_raw else "Red"
    return canon, winning_team


def process_match(match: dict, conn):
    """
    Core ETL pipeline adapted for Henrik Dev API JSON v3 format.
    
    Processes: matches → players → player_match_stats → rounds → 
               kill_events → player_round_stats → player_locations
    """
    metadata = match.get("metadata", {})
    players = match.get("players", {}).get("all_players", [])
    rounds_data = match.get("rounds", [])
    kills = match.get("kills", [])
    teams_data = match.get("teams", {})

    match_id = metadata.get("matchid")
    if not match_id:
        print("Skipping match: no match ID found in metadata.")
        return

    print(f"Processing Henrik Match ID: {match_id}")

    # Pre-compute lookup maps
    player_agent_map = _build_player_agent_map(players)
    player_team_map = _build_player_team_map(players)
    # Normalize team identity (Red/Blue even for UUID/premier matches) + winner.
    team_canon, winning_team = _build_team_normalizer(match)

    def canon_team(raw: str) -> str:
        return team_canon.get(raw, "Red")

    # Group kills by round number for opening kill detection
    kills_by_round: dict[int, list[dict]] = defaultdict(list)
    for kill in kills:
        kills_by_round[kill.get("round", 0)].append(kill)

    # Sort kills within each round by time
    for round_num in kills_by_round:
        kills_by_round[round_num].sort(key=lambda k: k.get("kill_time_in_round", 0))

    try:
        with conn.cursor() as cursor:
            # ── 1. Insert Match ──────────────────────────────────────────
            cursor.execute('''
                INSERT IGNORE INTO matches 
                (match_id, map_id, game_mode, queue_id, game_length_ms, 
                 started_at, season_id, rounds_played)
                VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s), %s, %s)
            ''', (
                match_id,
                metadata.get("map", "unknown"),
                metadata.get("mode", "unknown"),        # game_mode, e.g. "Competitive"
                metadata.get("queue"),                  # queue_id, e.g. "Standard" (was wrongly mode_id="competitive")
                metadata.get("game_length", 0) * 1000,  # seconds → ms
                metadata.get("game_start", 0),
                metadata.get("season_id"),
                metadata.get("rounds_played", 0),
            ))

            # ── 2. Insert Players and Player Match Stats ─────────────────
            for p in players:
                puuid = p["puuid"]
                stats = p.get("stats", {})
                hs_pct, bs_pct, ls_pct = _compute_hit_percentages(stats)
                player_canon_team = canon_team(p.get("team", ""))
                won = player_canon_team == winning_team

                cursor.execute('''
                    INSERT INTO players 
                    (puuid, game_name, tag_line, region, card_uuid)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        game_name = VALUES(game_name),
                        tag_line = VALUES(tag_line),
                        card_uuid = VALUES(card_uuid)
                ''', (
                    puuid,
                    p.get("name", "Unknown"),
                    p.get("tag", "0000"),
                    metadata.get("region", "na"),
                    p.get("player_card"),
                ))

                cursor.execute('''
                    INSERT IGNORE INTO player_match_stats
                    (match_id, puuid, team_id, agent_id, total_score, 
                     total_rounds, total_kills, total_deaths, total_assists,
                     headshot_pct, bodyshot_pct, legshot_pct, won, tier_id, tier_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    match_id,
                    puuid,
                    player_canon_team,
                    p.get("character", "Unknown"),
                    stats.get("score", 0),
                    metadata.get("rounds_played", 0),
                    stats.get("kills", 0),
                    stats.get("deaths", 0),
                    stats.get("assists", 0),
                    hs_pct,
                    bs_pct,
                    ls_pct,
                    won,
                    p.get("currenttier"),
                    p.get("currenttier_patched"),
                ))

            # ── 3. Process Rounds ────────────────────────────────────────
            # Store round_num → round_id mapping for kill and stats insertion
            round_id_map: dict[int, int] = {}

            for r_num, round_data in enumerate(rounds_data):
                # Extract plant/defuse data
                plant_events = round_data.get("plant_events", {}) or {}
                defuse_events = round_data.get("defuse_events", {}) or {}

                planted_by = plant_events.get("planted_by") or {}
                defused_by = defuse_events.get("defused_by") or {}

                cursor.execute('''
                    INSERT IGNORE INTO rounds
                    (match_id, round_num, round_result, winning_team,
                     bomb_planter, bomb_defuser, plant_time_ms, defuse_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    match_id,
                    r_num,
                    round_data.get("end_type", "unknown"),
                    canon_team(round_data.get("winning_team", "")),
                    planted_by.get("puuid"),
                    defused_by.get("puuid"),
                    plant_events.get("plant_time_in_round"),
                    defuse_events.get("defuse_time_in_round"),
                ))

                round_id = cursor.lastrowid
                if round_id == 0:
                    cursor.execute(
                        'SELECT id FROM rounds WHERE match_id=%s AND round_num=%s',
                        (match_id, r_num)
                    )
                    row = cursor.fetchone()
                    round_id = row["id"] if row else 0

                round_id_map[r_num] = round_id

                # ── 3a. Insert Player Round Stats ────────────────────────
                for ps in round_data.get("player_stats", []):
                    ps_puuid = ps.get("player_puuid", "")
                    economy = ps.get("economy", {}) or {}

                    # Count deaths for this player in this round from global kills
                    deaths_in_round = sum(
                        1 for k in kills_by_round.get(r_num, [])
                        if k.get("victim_puuid") == ps_puuid
                    )

                    # Count assists for this player in this round from global kills
                    assists_in_round = sum(
                        1 for k in kills_by_round.get(r_num, [])
                        for a in k.get("assistants", [])
                        if a.get("assistant_puuid") == ps_puuid
                    )

                    # Sum damage received from other players' damage_events
                    damage_received = 0
                    for other_ps in round_data.get("player_stats", []):
                        if other_ps.get("player_puuid") == ps_puuid:
                            continue
                        for dmg in other_ps.get("damage_events", []):
                            if dmg.get("receiver_puuid") == ps_puuid:
                                damage_received += dmg.get("damage", 0)

                    cursor.execute('''
                        INSERT IGNORE INTO player_round_stats
                        (round_id, puuid, agent_id, team_id, score, kills,
                         deaths, assists, damage_dealt, damage_received,
                         economy_loadout_value, economy_remaining, economy_spent,
                         was_afk, was_penalized)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        round_id,
                        ps_puuid,
                        player_agent_map.get(ps_puuid, "Unknown"),
                        canon_team(ps.get("player_team", "")),
                        ps.get("score", 0),
                        ps.get("kills", 0),
                        deaths_in_round,
                        assists_in_round,
                        ps.get("damage", 0),
                        damage_received,
                        economy.get("loadout_value", 0),
                        economy.get("remaining", 0),
                        economy.get("spent", 0),
                        ps.get("was_afk", False),
                        ps.get("was_penalized", False),
                    ))

            # ── 4. Process Global Kills Array ────────────────────────────
            # Track inserted player locations to avoid duplicates
            inserted_locations: set[tuple[int, str]] = set()

            for round_num, round_kills in kills_by_round.items():
                round_id = round_id_map.get(round_num)
                if not round_id:
                    continue

                # Get the round data for damage type inference
                round_data = rounds_data[round_num] if round_num < len(rounds_data) else {}

                for kill_idx, kill in enumerate(round_kills):
                    # Determine if this is the opening kill of the round
                    is_opening_kill = (kill_idx == 0)

                    # Get killer location by finding their entry in player_locations_on_kill
                    killer_x, killer_y = _find_killer_location(kill)

                    # Get victim death location
                    victim_loc = kill.get("victim_death_location", {})
                    victim_x = victim_loc.get("x", 0)
                    victim_y = victim_loc.get("y", 0)

                    # Infer finishing damage type from round damage events
                    damage_type = _determine_finishing_damage_type(
                        round_data,
                        kill.get("killer_puuid", ""),
                        kill.get("victim_puuid", ""),
                    )

                    # Count assistants
                    assistants = kill.get("assistants", [])
                    assistants_count = len(assistants)

                    cursor.execute('''
                        INSERT IGNORE INTO kill_events
                        (round_id, killer_puuid, victim_puuid, time_in_round_ms,
                         killer_x, killer_y, victim_x, victim_y,
                         weapon, finishing_damage_type,
                         is_opening_kill, assistants_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        round_id,
                        kill.get("killer_puuid", ""),
                        kill.get("victim_puuid", ""),
                        kill.get("kill_time_in_round", 0),
                        killer_x,
                        killer_y,
                        victim_x,
                        victim_y,
                        kill.get("damage_weapon_name", "Unknown"),
                        damage_type,
                        is_opening_kill,
                        assistants_count,
                    ))

                    # ── 4a. Extract Player Locations from Kill Snapshots ─
                    for loc_entry in kill.get("player_locations_on_kill", []):
                        loc_puuid = loc_entry.get("player_puuid", "")
                        loc_key = (round_id, loc_puuid)

                        # Only insert one location per player per round
                        # (use the first kill snapshot, closest to round start)
                        if loc_key in inserted_locations:
                            continue
                        inserted_locations.add(loc_key)

                        location = loc_entry.get("location", {})
                        cursor.execute('''
                            INSERT IGNORE INTO player_locations
                            (round_id, puuid, x, y, view_radians, capture_time_ms)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            round_id,
                            loc_puuid,
                            location.get("x", 0),
                            location.get("y", 0),
                            loc_entry.get("view_radians", 0),
                            kill.get("kill_time_in_round", 0),
                        ))

        conn.commit()
        print(f"Successfully processed Henrik Match {match_id} into MariaDB.")
        print(f"  - {len(players)} players")
        print(f"  - {len(rounds_data)} rounds")
        print(f"  - {len(kills)} kill events")

    except Exception as e:
        conn.rollback()
        print(f"Database insertion failed for match {match_id}: {e}")
        raise


def process_match_file(filepath: str):
    """Load a Henrik match JSON file and process it into the database."""
    with open(filepath) as f:
        match = json.load(f)
    conn = get_db_connection()
    try:
        process_match(match, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        process_match_file(sys.argv[1])
    else:
        print("Henrik ETL Script Ready.")
        print("Usage: python etl.py <path_to_henrik_match.json>")
