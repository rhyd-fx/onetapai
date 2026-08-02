"""Read queries backing the API — plain SQL over the MariaDB schema.

All functions take an open pymysql connection (DictCursor) and return plain
JSON-serializable Python values.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime

# Default "ranked" scope: the two modes that share the competitive stat model.
# Passed as the default game_modes so callers that don't specify a filter keep
# the historical competitive-only behavior.
RANKED_MODES: tuple[str, ...] = ("Competitive", "Premier")


def _match_filters(
    game_modes: Sequence[str] | None,
    season_id: str | None,
    alias: str = "m",
) -> tuple[str, list]:
    """Build the shared `matches` WHERE fragment used by the stat queries.

    Returns (filter_str, params) where filter_str is either "" or begins with
    "AND ", ready to splice after an existing `WHERE ...` clause.

    game_modes semantics:
      - non-empty        -> `alias.game_mode IN (...)` for those modes
      - None or empty [] -> no mode filter (all modes)
    """
    clauses: list[str] = []
    params: list = []
    if game_modes:
        placeholders = ",".join(["%s"] * len(game_modes))
        clauses.append(f"{alias}.game_mode IN ({placeholders})")
        params.extend(game_modes)
    if season_id:
        clauses.append(f"{alias}.season_id = %s")
        params.append(season_id)
    filter_str = " AND ".join(clauses)
    return (f"AND {filter_str}" if filter_str else ""), params

_FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS coaching_feedback (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    puuid          CHAR(78)        NULL,
    question       TEXT            NOT NULL,
    answer_excerpt TEXT            NULL,
    rating         TINYINT         NOT NULL,
    sources_json   JSON            NULL,
    created_at     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_cf_rating (rating, created_at)
) ENGINE=InnoDB
"""


def record_feedback(
    conn,
    puuid: str | None,
    question: str,
    rating: int,
    answer_excerpt: str | None = None,
    sources: list | None = None,
) -> None:
    """Persist a thumbs up/down. Ensures the table exists (idempotent) so it
    works even on a DB created before the table was added to init.sql."""
    with conn.cursor() as cur:
        cur.execute(_FEEDBACK_DDL)
        cur.execute(
            """
            INSERT INTO coaching_feedback
                (puuid, question, answer_excerpt, rating, sources_json)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                puuid,
                question,
                answer_excerpt,
                rating,
                json.dumps(sources) if sources else None,
            ),
        )
    conn.commit()


def _f(v):
    """Coerce Decimal/None to float|None for clean JSON."""
    return float(v) if v is not None else None


def resolve_puuid(conn, name: str, tag: str) -> str | None:
    """Look up a puuid by Riot ID (game_name + tag_line)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT puuid FROM players WHERE game_name = %s AND tag_line = %s LIMIT 1",
            (name, tag),
        )
        row = cur.fetchone()
        return row["puuid"] if row else None


def get_player_summary(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict | None:
    """Identity + aggregate stats across matches filtered by season and game mode(s)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT puuid, game_name, tag_line, region, card_uuid FROM players WHERE puuid = %s",
            (puuid,),
        )
        player = cur.fetchone()
        if not player:
            return None

        filter_str, params = _match_filters(game_modes, season_id)

        cur.execute(
            f"""
            SELECT COUNT(*)            AS games,
                   SUM(pms.won)        AS wins,
                   AVG(pms.acs)        AS avg_acs,
                   AVG(pms.headshot_pct)   AS avg_hs,
                   AVG(pms.bodyshot_pct)   AS avg_bs,
                   AVG(pms.legshot_pct)    AS avg_ls,
                   SUM(pms.total_kills)    AS kills,
                   SUM(pms.total_deaths)   AS deaths,
                   SUM(pms.total_assists)  AS assists
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s {filter_str}
            """,
            [puuid] + params,
        )
        agg = cur.fetchone() or {}

        cur.execute(
            f"""
            SELECT pms.agent_id, COUNT(*) AS n
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s {filter_str}
            GROUP BY pms.agent_id
            ORDER BY n DESC
            LIMIT 1
            """,
            [puuid] + params,
        )
        agent_row = cur.fetchone()

    games = int(agg.get("games") or 0)
    wins = int(agg.get("wins") or 0)
    return {
        "game_name": player["game_name"],
        "tag_line": player["tag_line"],
        "region": player["region"],
        "card_uuid": player["card_uuid"],
        "games": games,
        "wins": wins,
        "win_rate": round(wins / games * 100, 1) if games else None,
        "avg_acs": round(_f(agg.get("avg_acs")) or 0, 1),
        "headshot_pct": _f(agg.get("avg_hs")),
        "bodyshot_pct": _f(agg.get("avg_bs")),
        "legshot_pct": _f(agg.get("avg_ls")),
        "kills": int(agg.get("kills") or 0),
        "deaths": int(agg.get("deaths") or 0),
        "assists": int(agg.get("assists") or 0),
        "main_agent": agent_row["agent_id"] if agent_row else None,
    }


def get_player_seasons(conn, puuid: str) -> list[str]:
    """Retrieve distinct season IDs played by the player, sorted newest to oldest."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.season_id, MIN(m.started_at) AS first_match_date
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s AND m.season_id IS NOT NULL
            GROUP BY m.season_id
            ORDER BY first_match_date DESC
            """,
            (puuid,),
        )
        rows = cur.fetchall()
    return [r["season_id"] for r in rows]


def get_engagement_locations(conn, puuid: str, map_id: str, limit: int = 50) -> dict:
    """Raw kill/death world coordinates for a player on a map.

    Returns {"deaths": [(x, y), ...], "kills": [(x, y), ...]} in raw Unreal units.
    Exact (0,0) sentinels (failed location lookups) are excluded.
    """
    deaths: list[tuple[float, float]] = []
    kills: list[tuple[float, float]] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ke.victim_x AS x, ke.victim_y AS y
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.victim_puuid = %s AND m.map_id = %s
              AND NOT (ke.victim_x = 0 AND ke.victim_y = 0)
            ORDER BY m.started_at DESC
            LIMIT %s
            """,
            (puuid, map_id, int(limit)),
        )
        deaths = [(r["x"], r["y"]) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT ke.killer_x AS x, ke.killer_y AS y
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.killer_puuid = %s AND m.map_id = %s
              AND NOT (ke.killer_x = 0 AND ke.killer_y = 0)
            ORDER BY m.started_at DESC
            LIMIT %s
            """,
            (puuid, map_id, int(limit)),
        )
        kills = [(r["x"], r["y"]) for r in cur.fetchall()]

    return {"deaths": deaths, "kills": kills}


def get_telemetry(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict:
    """Advanced per-round telemetry derivable from ingested data.

    - movement_error_pct: % of death-rounds where the player dealt 0 damage
      (the plan's "moving while shooting" signal, §6.3).
    - opening_duel_win_pct: first-engagement (opening) kills vs opening deaths.
    - avg_time_to_damage_s: mean time into the round of the player's first
      engagement (kill or death).
    - multikill_pct: % of rounds with 2+ kills.
    """
    filter_str, params = _match_filters(game_modes, season_id)

    t = {
        "rounds": 0,
        "adr": None,                 # average damage per round (raw performance)
        "movement_error_pct": None,
        "opening_duel_win_pct": None,
        "first_kills": None,         # opening kills won
        "first_deaths": None,        # opening deaths taken
        "fk_fd_diff": None,          # first_kills - first_deaths (entry impact)
        "avg_time_to_damage_s": None,
        "multikill_pct": None,
    }
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*) AS rounds,
                   SUM(prs.damage_dealt) AS total_damage,
                   SUM(CASE WHEN prs.kills >= 2 THEN 1 ELSE 0 END) AS multi,
                   SUM(CASE WHEN prs.deaths > 0 THEN 1 ELSE 0 END) AS death_rounds,
                   SUM(CASE WHEN prs.deaths > 0 AND prs.damage_dealt = 0 THEN 1 ELSE 0 END) AS zero_dmg
            FROM player_round_stats prs
            JOIN rounds r ON prs.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE prs.puuid = %s {filter_str}
            """,
            [puuid] + params,
        )
        r = cur.fetchone() or {}
        rounds = int(r.get("rounds") or 0)
        t["rounds"] = rounds
        if rounds:
            t["adr"] = round(int(r.get("total_damage") or 0) / rounds, 1)
            t["multikill_pct"] = round(int(r.get("multi") or 0) / rounds * 100, 1)
        death_rounds = int(r.get("death_rounds") or 0)
        if death_rounds:
            t["movement_error_pct"] = round(int(r.get("zero_dmg") or 0) / death_rounds * 100, 1)

        cur.execute(
            f"""
            SELECT SUM(CASE WHEN ke.killer_puuid = %s THEN 1 ELSE 0 END) AS opening_kills,
                   SUM(CASE WHEN ke.victim_puuid = %s THEN 1 ELSE 0 END) AS opening_deaths
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.is_opening_kill = TRUE
              AND (ke.killer_puuid = %s OR ke.victim_puuid = %s)
              {filter_str}
            """,
            [puuid, puuid, puuid, puuid] + params,
        )
        o = cur.fetchone() or {}
        ok, od = int(o.get("opening_kills") or 0), int(o.get("opening_deaths") or 0)
        if ok + od > 0:
            t["opening_duel_win_pct"] = round(ok / (ok + od) * 100, 1)
            t["first_kills"] = ok
            t["first_deaths"] = od
            t["fk_fd_diff"] = ok - od

        cur.execute(
            f"""
            SELECT AVG(first_ms) AS ttd FROM (
                SELECT ke.round_id, MIN(ke.time_in_round_ms) AS first_ms
                FROM kill_events ke
                JOIN rounds r ON ke.round_id = r.id
                JOIN matches m ON r.match_id = m.match_id
                WHERE (ke.killer_puuid = %s OR ke.victim_puuid = %s)
                  {filter_str}
                GROUP BY ke.round_id
            ) x
            """,
            [puuid, puuid] + params,
        )
        tt = cur.fetchone() or {}
        if tt.get("ttd") is not None:
            t["avg_time_to_damage_s"] = round(float(tt["ttd"]) / 1000, 1)
    return t


def get_match_timeline(conn, puuid: str, limit: int = 100) -> list[tuple[float, float]]:
    """Chronological (unix_ts, acs) pairs for competitive matches."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT UNIX_TIMESTAMP(m.started_at) AS ts, pms.acs AS acs
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s AND m.game_mode IN ('Competitive', 'Premier')
            ORDER BY m.started_at DESC
            LIMIT %s
            """,
            (puuid, int(limit)),
        )
        # Most recent N, re-sorted chronologically for trend analysis.
        rows = list(reversed(cur.fetchall()))
    return [(float(r["ts"]), float(r["acs"] or 0)) for r in rows if r["ts"] is not None]


def get_map_coord_samples(conn, map_id: str, limit: int = 20000) -> list[tuple[float, float]]:
    """All (killer + victim) coordinates recorded on a map, for deriving that
    map's true coordinate bounds. Excludes (0,0) sentinels."""
    with conn.cursor() as cur:
        cur.execute(
            """
            (SELECT ke.killer_x AS x, ke.killer_y AS y
             FROM kill_events ke
             JOIN rounds r ON ke.round_id = r.id
             JOIN matches m ON r.match_id = m.match_id
             WHERE m.map_id = %s AND NOT (ke.killer_x = 0 AND ke.killer_y = 0))
            UNION ALL
            (SELECT ke.victim_x AS x, ke.victim_y AS y
             FROM kill_events ke
             JOIN rounds r ON ke.round_id = r.id
             JOIN matches m ON r.match_id = m.match_id
             WHERE m.map_id = %s AND NOT (ke.victim_x = 0 AND ke.victim_y = 0))
            LIMIT %s
            """,
            (map_id, map_id, int(limit)),
        )
        return [(r["x"], r["y"]) for r in cur.fetchall()]


def get_acs_trajectory(conn, puuid: str, limit: int = 20, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> list[dict]:
    """Per-match ACS over time (chronological) for trajectory / tilt charts."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT pms.match_id, m.map_id, m.started_at, pms.acs, pms.won,
                   pms.headshot_pct, pms.bodyshot_pct, pms.agent_id AS agent,
                   pms.total_kills, pms.total_deaths, pms.total_assists,
                   pms.tier_id, pms.tier_name,
                   (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.match_id AND r.winning_team = pms.team_id) AS team_score,
                   (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.match_id AND r.winning_team != pms.team_id) AS enemy_score
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s {filter_str}
            ORDER BY m.started_at DESC
            LIMIT %s
            """,
            [puuid] + params + [int(limit)],
        )
        # Most recent N, re-sorted chronologically for the trajectory chart.
        rows = list(reversed(cur.fetchall()))

    trajectory = []
    for r in rows:
        started = r["started_at"]
        trajectory.append(
            {
                "match_id": r["match_id"],
                "map": r["map_id"],
                "started_at": started.isoformat() if isinstance(started, datetime) else started,
                "acs": round(_f(r["acs"]) or 0, 1),
                "won": bool(r["won"]),
                "headshot_pct": _f(r["headshot_pct"]),
                "bodyshot_pct": _f(r["bodyshot_pct"]),
                "agent": r["agent"],
                "kills": int(r["total_kills"]) if r["total_kills"] is not None else 0,
                "deaths": int(r["total_deaths"]) if r["total_deaths"] is not None else 0,
                "assists": int(r["total_assists"]) if r["total_assists"] is not None else 0,
                "team_score": int(r["team_score"]) if r["team_score"] is not None else 0,
                "enemy_score": int(r["enemy_score"]) if r["enemy_score"] is not None else 0,
                "tier_id": int(r["tier_id"]) if r["tier_id"] is not None else 0,
                "tier_name": r["tier_name"] or "Unranked",
            }
        )
    return trajectory


def get_top_maps(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> list[dict]:
    """Retrieve map statistics for a player, sorted by win rate."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT m.map_id AS map,
                   COUNT(*) AS games,
                   SUM(pms.won) AS wins,
                   SUM(NOT pms.won) AS losses,
                   (SUM(pms.won) / COUNT(*)) * 100 AS win_rate
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s {filter_str}
            GROUP BY m.map_id
            ORDER BY win_rate DESC, games DESC
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()
    return [
        {
            "map": r["map"],
            "games": int(r["games"]),
            "wins": int(r["wins"]),
            "losses": int(r["losses"]),
            "win_rate": round(float(r["win_rate"]), 1) if r["win_rate"] is not None else 0.0,
        }
        for r in rows
    ]


def get_top_weapons(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> list[dict]:
    """Retrieve weapon kill and shot distribution statistics for a player, sorted by kills."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT ke.weapon,
                   COUNT(*) AS kills,
                   SUM(CASE WHEN ke.finishing_damage_type = 'headshot' THEN 1 ELSE 0 END) AS headshots,
                   SUM(CASE WHEN ke.finishing_damage_type = 'bodyshot' THEN 1 ELSE 0 END) AS bodyshots,
                   SUM(CASE WHEN ke.finishing_damage_type = 'legshot' THEN 1 ELSE 0 END) AS legshots
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.killer_puuid = %s {filter_str}
            GROUP BY ke.weapon
            ORDER BY kills DESC
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()

    weapons = []
    for r in rows:
        kills = int(r["kills"])
        hs = int(r["headshots"])
        bs = int(r["bodyshots"])
        ls = int(r["legshots"])
        total_shots = hs + bs + ls
        weapons.append({
            "weapon": r["weapon"],
            "kills": kills,
            "headshot_pct": round(hs / total_shots * 100, 1) if total_shots > 0 else 0.0,
            "bodyshot_pct": round(bs / total_shots * 100, 1) if total_shots > 0 else 0.0,
            "legshot_pct": round(ls / total_shots * 100, 1) if total_shots > 0 else 0.0,
        })
    return weapons


def get_aim_by_distance(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> list[dict]:
    """Calculate shot distribution (headshot/bodyshot/legshot) percentages categorized by distance."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT 
                CASE 
                    WHEN ke.engagement_distance < 1000 THEN 'close'
                    WHEN ke.engagement_distance BETWEEN 1000 AND 2000 THEN 'medium'
                    ELSE 'long'
                END AS range_category,
                COUNT(*) AS kills,
                SUM(CASE WHEN ke.finishing_damage_type = 'headshot' THEN 1 ELSE 0 END) AS headshots,
                SUM(CASE WHEN ke.finishing_damage_type = 'bodyshot' THEN 1 ELSE 0 END) AS bodyshots,
                SUM(CASE WHEN ke.finishing_damage_type = 'legshot' THEN 1 ELSE 0 END) AS legshots
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.killer_puuid = %s {filter_str}
            GROUP BY range_category
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()

    ranges = []
    for cat in ['close', 'medium', 'long']:
        match = next((r for r in rows if r["range_category"] == cat), None)
        if match:
            kills = int(match["kills"])
            hs = int(match["headshots"])
            bs = int(match["bodyshots"])
            ls = int(match["legshots"])
            total = hs + bs + ls
            ranges.append({
                "range": cat,
                "kills": kills,
                "headshot_pct": round(hs / total * 100, 1) if total > 0 else 0.0,
                "bodyshot_pct": round(bs / total * 100, 1) if total > 0 else 0.0,
                "legshot_pct": round(ls / total * 100, 1) if total > 0 else 0.0,
            })
        else:
            ranges.append({
                "range": cat,
                "kills": 0,
                "headshot_pct": 0.0,
                "bodyshot_pct": 0.0,
                "legshot_pct": 0.0,
            })
    return ranges


def get_economy_efficiency(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict:
    """Calculate win rates by economy class and track eco round throws."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT 
                vec.economy_class,
                COUNT(*) AS rounds,
                SUM(CASE WHEN r.winning_team = prs.team_id THEN 1 ELSE 0 END) AS wins
            FROM player_round_stats prs
            JOIN v_round_economy_class vec ON prs.id = vec.prs_id
            JOIN rounds r ON prs.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE prs.puuid = %s {filter_str}
            GROUP BY vec.economy_class
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()
        
        cur.execute(
            f"""
            SELECT COUNT(DISTINCT prs.round_id) AS eco_throws
            FROM player_round_stats prs
            JOIN rounds r ON prs.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE prs.puuid = %s {filter_str}
              AND prs.economy_loadout_value >= 4500
              AND r.winning_team != prs.team_id
              AND (
                  SELECT AVG(enemy.economy_loadout_value)
                  FROM player_round_stats enemy
                  WHERE enemy.round_id = prs.round_id
                    AND enemy.team_id != prs.team_id
              ) < 2000
            """,
            [puuid] + params,
        )
        throw_row = cur.fetchone()
        eco_throws = throw_row["eco_throws"] if throw_row else 0

    econ_stats = {}
    for r in rows:
        cat = r["economy_class"]
        rounds = int(r["rounds"])
        wins = int(r["wins"])
        econ_stats[cat] = {
            "rounds": rounds,
            "wins": wins,
            "win_rate": round(wins / rounds * 100, 1) if rounds > 0 else 0.0
        }
        
    for cat in ['eco', 'half_buy', 'force_buy', 'full_buy']:
        if cat not in econ_stats:
            econ_stats[cat] = {"rounds": 0, "wins": 0, "win_rate": 0.0}

    return {
        "by_class": econ_stats,
        "eco_throws": int(eco_throws)
    }


def get_side_bias(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict:
    """Compare Attack vs. Defense round win rates and calculate early deaths on defense."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT prs.team_id, r.round_num, r.winning_team, prs.deaths, prs.damage_dealt
            FROM player_round_stats prs
            JOIN rounds r ON prs.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE prs.puuid = %s {filter_str}
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()

    attack_rounds = 0
    attack_wins = 0
    defense_rounds = 0
    defense_wins = 0
    defense_deaths = 0

    for r in rows:
        team = r["team_id"]
        round_num = int(r["round_num"])
        won_round = (r["winning_team"] == team)
        
        is_attack = False
        if round_num < 12:
            is_attack = (team == "Red")
        elif round_num < 24:
            is_attack = (team == "Blue")
        else:
            is_attack = (team == "Red") if (round_num % 2 == 0) else (team == "Blue")
            
        if is_attack:
            attack_rounds += 1
            if won_round:
                attack_wins += 1
        else:
            defense_rounds += 1
            if won_round:
                defense_wins += 1
            if int(r["deaths"]) > 0:
                defense_deaths += 1

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            JOIN player_round_stats prs ON prs.round_id = r.id AND prs.puuid = %s
            WHERE ke.victim_puuid = %s
              AND ke.time_in_round_ms < 15000
              {filter_str}
              AND (
                  (prs.team_id = 'Blue' AND r.round_num < 12) OR
                  (prs.team_id = 'Red' AND r.round_num >= 12 AND r.round_num < 24) OR
                  (prs.team_id = 'Blue' AND r.round_num >= 24 AND r.round_num %% 2 = 0) OR
                  (prs.team_id = 'Red' AND r.round_num >= 24 AND r.round_num %% 2 != 0)
              )
            """,
            [puuid, puuid] + params,
        )
        early_defense_deaths = cur.fetchone()["count"]

    return {
        "attack_win_pct": round(attack_wins / attack_rounds * 100, 1) if attack_rounds > 0 else 0.0,
        "attack_rounds": attack_rounds,
        "defense_win_pct": round(defense_wins / defense_rounds * 100, 1) if defense_rounds > 0 else 0.0,
        "defense_rounds": defense_rounds,
        "early_defense_death_pct": round(early_defense_deaths / defense_rounds * 100, 1) if defense_rounds > 0 else 0.0,
        "early_defense_deaths": early_defense_deaths,
    }


def get_hardware_check(conn, puuid: str) -> dict:
    """Retrieve player hardware configuration (eDPI, mouse model, refresh rate)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT mouse_dpi, in_game_sens, edpi, mouse_model, monitor_refresh_rate
            FROM player_hardware_profiles
            WHERE puuid = %s
            LIMIT 1
            """,
            (puuid,),
        )
        row = cur.fetchone()
        
    if row:
        return {
            "mouse_dpi": int(row["mouse_dpi"]),
            "in_game_sens": float(row["in_game_sens"]),
            "edpi": float(row["edpi"]),
            "mouse_model": row["mouse_model"] or "Generic Mouse",
            "monitor_refresh_rate": int(row["monitor_refresh_rate"]) if row["monitor_refresh_rate"] else 144,
        }
    else:
        return {
            "mouse_dpi": 800,
            "in_game_sens": 0.35,
            "edpi": 280.0,
            "mouse_model": "Generic Mouse",
            "monitor_refresh_rate": 144,
        }


def get_matchup_diagnostics(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict:
    """Analyze player death events to find matchup errors and utility deaths."""
    filter_str, params = _match_filters(game_modes, season_id)

    gun_list = (
        'Vandal','Phantom','Sheriff','Spectre','Classic','Ghost','Marshal',
        'Operator','Guardian','Odin','Stinger','Bucky','Judge','Ares','Bulldog',
        'Outlaw','Melee','Shorty','Frenzy'
    )
    
    with conn.cursor() as cur:
        # 1. Top killer agents
        cur.execute(
            f"""
            SELECT pms_k.agent_id AS agent, COUNT(*) AS count
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            JOIN player_match_stats pms_k ON pms_k.match_id = m.match_id AND pms_k.puuid = ke.killer_puuid
            WHERE ke.victim_puuid = %s {filter_str}
            GROUP BY agent
            ORDER BY count DESC
            """,
            [puuid] + params
        )
        killer_agents = cur.fetchall()

        # 2. Utility deaths (not killed by standard gun/melee)
        cur.execute(
            f"""
            SELECT ke.weapon AS ability, COUNT(*) AS count
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.victim_puuid = %s 
              AND ke.weapon NOT IN {gun_list}
              {filter_str}
            GROUP BY ability
            ORDER BY count DESC
            LIMIT 5
            """,
            [puuid] + params
        )
        utility_deaths = cur.fetchall()

        # 3. Overall gun vs utility death counts
        cur.execute(
            f"""
            SELECT 
                SUM(CASE WHEN ke.weapon IN {gun_list} THEN 1 ELSE 0 END) AS gun_deaths,
                SUM(CASE WHEN ke.weapon NOT IN {gun_list} THEN 1 ELSE 0 END) AS utility_deaths
            FROM kill_events ke
            JOIN rounds r ON ke.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE ke.victim_puuid = %s {filter_str}
            """,
            [puuid] + params
        )
        death_types = cur.fetchone() or {"gun_deaths": 0, "utility_deaths": 0}

    # Group killers by role
    role_deaths = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0, "Unknown": 0}
    agent_roles = {
        "jett": "Duelist", "raze": "Duelist", "neon": "Duelist", "reyna": "Duelist", "phoenix": "Duelist", "yoru": "Duelist", "iso": "Duelist",
        "sova": "Initiator", "fade": "Initiator", "breach": "Initiator", "skye": "Initiator", "kay/o": "Initiator", "gekko": "Initiator",
        "omen": "Controller", "viper": "Controller", "brimstone": "Controller", "astra": "Controller", "harbor": "Controller", "clove": "Controller",
        "sage": "Sentinel", "cypher": "Sentinel", "killjoy": "Sentinel", "chamber": "Sentinel", "deadlock": "Sentinel"
    }
    
    for row in killer_agents:
        agent = (row["agent"] or "").lower()
        count = int(row["count"])
        role = agent_roles.get(agent, "Unknown")
        role_deaths[role] += count

    return {
        "killer_agents": [{"agent": r["agent"], "deaths": int(r["count"])} for r in killer_agents[:5]],
        "killer_roles": role_deaths,
        "utility_deaths": [{"ability": r["ability"], "deaths": int(r["count"])} for r in utility_deaths],
        "gun_deaths_count": int(death_types.get("gun_deaths") or 0),
        "utility_deaths_count": int(death_types.get("utility_deaths") or 0)
    }


def get_economy_split(conn, puuid: str, season_id: str | None = None, game_modes: Sequence[str] | None = RANKED_MODES) -> dict:
    """Calculate ACS and round counts grouped by economy class (eco/half_buy/force_buy/full_buy)."""
    filter_str, params = _match_filters(game_modes, season_id)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT 
                vec.economy_class,
                COUNT(*) AS rounds,
                AVG(vec.score) AS avg_score
            FROM player_round_stats prs
            JOIN v_round_economy_class vec ON prs.id = vec.prs_id
            JOIN rounds r ON prs.round_id = r.id
            JOIN matches m ON r.match_id = m.match_id
            WHERE prs.puuid = %s {filter_str}
            GROUP BY vec.economy_class
            """,
            [puuid] + params,
        )
        rows = cur.fetchall()

    split = {}
    for r in rows:
        cat = r["economy_class"]
        rounds = int(r["rounds"])
        avg_score = float(r["avg_score"]) if r["avg_score"] is not None else 0.0
        split[cat] = {
            "rounds": rounds,
            "avg_acs": round(avg_score, 1)
        }

    for cat in ['eco', 'half_buy', 'force_buy', 'full_buy']:
        if cat not in split:
            split[cat] = {"rounds": 0, "avg_acs": 0.0}

    return split





def find_recent_match(
    conn,
    puuid: str,
    map_name: str | None = None,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """Most recent match the player appears in, optionally filtered by map.

    map_name matches matches.map_id case-insensitively ("lotus" -> "Lotus").
    """
    map_clause = "AND LOWER(m.map_id) = LOWER(%s)" if map_name else ""
    filter_str, params = _match_filters(game_modes, None)
    sql_params = [puuid] + ([map_name] if map_name else []) + params

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT pms.match_id, m.map_id, m.started_at, m.rounds_played,
                   m.game_mode,
                   pms.team_id, pms.agent_id, pms.acs, pms.won,
                   pms.total_kills, pms.total_deaths, pms.total_assists,
                   pms.headshot_pct, pms.tier_name,
                   (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.match_id AND r.winning_team = pms.team_id) AS team_score,
                   (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.match_id AND r.winning_team != pms.team_id) AS enemy_score
            FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.match_id
            WHERE pms.puuid = %s {map_clause} {filter_str}
            ORDER BY m.started_at DESC
            LIMIT 1
            """,
            sql_params,
        )
        row = cur.fetchone()
    if not row:
        return None

    started = row["started_at"]
    return {
        "match_id": row["match_id"],
        "map": row["map_id"],
        "game_mode": row["game_mode"] or "Unknown",
        "started_at": started.isoformat() if isinstance(started, datetime) else started,
        "agent": row["agent_id"],
        "team": row["team_id"],
        "won": bool(row["won"]),
        "team_score": int(row["team_score"] or 0),
        "enemy_score": int(row["enemy_score"] or 0),
        "acs": round(_f(row["acs"]) or 0, 1),
        "kills": int(row["total_kills"] or 0),
        "deaths": int(row["total_deaths"] or 0),
        "assists": int(row["total_assists"] or 0),
        "headshot_pct": round((_f(row["headshot_pct"]) or 0) * 100, 1),
        "tier_name": row["tier_name"] or "Unranked",
    }


def _attacking(team: str, round_num: int, half_len: int = 12) -> bool:
    # Same side convention as get_side_bias: Red attacks the first half,
    # Blue the second half, overtime alternates. half_len is 12 for standard
    # modes, 4 for Swiftplay.
    if round_num < half_len:
        return team == "Red"
    if round_num < 2 * half_len:
        return team == "Blue"
    return (team == "Red") if (round_num % 2 == 0) else (team == "Blue")


def get_match_rounds(conn, match_id: str, puuid: str) -> list[dict]:
    """Round-by-round view of one match from the player's perspective.

    Feeds the coach LLM prompt: per round — result, side, player K/D/A,
    damage, loadout economy class, opening duel involvement, plant/defuse.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT game_mode FROM matches WHERE match_id = %s", (match_id,))
        mode_row = cur.fetchone()
        game_mode = (mode_row or {}).get("game_mode") or ""
        # Swiftplay swaps sides after 4 rounds; standard modes after 12. For
        # other modes (Spike Rush etc.) the convention is unknown — side is
        # omitted rather than guessed wrong.
        half_len = {"Swiftplay": 4}.get(game_mode, 12)
        side_known = game_mode in ("Competitive", "Premier", "Unrated", "Swiftplay", "Custom Game")

        cur.execute(
            """
            SELECT r.id AS round_id, r.round_num, r.round_result, r.winning_team,
                   r.bomb_planter, r.bomb_defuser,
                   prs.team_id, prs.kills, prs.deaths, prs.assists,
                   prs.damage_dealt, prs.damage_received,
                   prs.economy_loadout_value, prs.economy_spent, prs.was_afk
            FROM rounds r
            JOIN player_round_stats prs ON prs.round_id = r.id AND prs.puuid = %s
            WHERE r.match_id = %s
            ORDER BY r.round_num
            """,
            (puuid, match_id),
        )
        rounds = cur.fetchall()
        if not rounds:
            return []

        round_ids = [r["round_id"] for r in rounds]
        placeholders = ",".join(["%s"] * len(round_ids))
        cur.execute(
            f"""
            SELECT round_id, killer_puuid, victim_puuid, weapon,
                   finishing_damage_type, time_in_round_ms, is_opening_kill
            FROM kill_events
            WHERE round_id IN ({placeholders})
              AND (killer_puuid = %s OR victim_puuid = %s)
            ORDER BY round_id, time_in_round_ms
            """,
            round_ids + [puuid, puuid],
        )
        events = cur.fetchall()

    events_by_round: dict[int, list[dict]] = {}
    for e in events:
        events_by_round.setdefault(e["round_id"], []).append(e)

    out = []
    for r in rounds:
        team = r["team_id"]
        num = int(r["round_num"])
        loadout = int(r["economy_loadout_value"] or 0)
        # Buckets mirror v_round_economy_class in db/init.sql.
        if loadout < 2000:
            eco = "eco"
        elif loadout < 3900:
            eco = "half_buy"
        elif loadout < 4500:
            eco = "force_buy"
        else:
            eco = "full_buy"

        opening = None
        my_kills: list[dict] = []
        death: dict | None = None
        for e in events_by_round.get(r["round_id"], []):
            is_kill = e["killer_puuid"] == puuid
            if e["is_opening_kill"]:
                opening = "won" if is_kill else "lost"
            entry = {
                "weapon": e["weapon"],
                "headshot": e["finishing_damage_type"] == "headshot",
                "at_sec": round(int(e["time_in_round_ms"]) / 1000, 1),
            }
            if is_kill:
                my_kills.append(entry)
            else:
                death = entry

        out.append(
            {
                "round": num + 1,  # 1-based for humans/LLM
                "side": ("attack" if _attacking(team, num, half_len) else "defense") if side_known else "?",
                "won": r["winning_team"] == team,
                "result": r["round_result"],
                "kills": int(r["kills"] or 0),
                "deaths": int(r["deaths"] or 0),
                "assists": int(r["assists"] or 0),
                "damage_dealt": int(r["damage_dealt"] or 0),
                "damage_received": int(r["damage_received"] or 0),
                "loadout_value": loadout,
                "economy_class": eco,
                "opening_duel": opening,
                "kill_details": my_kills,
                "death_detail": death,
                "planted_bomb": r["bomb_planter"] == puuid,
                "defused_bomb": r["bomb_defuser"] == puuid,
                "was_afk": bool(r["was_afk"]),
            }
        )
    return out


def get_round_patterns(
    conn,
    puuid: str,
    match_limit: int = 20,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """Cross-match round-level patterns over the player's recent matches.

    Answers "do I always lose pistols?"-style questions: pistol record and
    conversion, bounce-back vs momentum win rates, early deaths and opening
    duels split by side. Returns None when no round data exists.
    """
    filter_str, params = _match_filters(game_modes, None)

    with conn.cursor() as cur:
        # Per-round rows for the player's most recent N matches, ordered so
        # momentum/conversion can be computed by walking each match.
        cur.execute(
            f"""
            SELECT r.id AS round_id, r.match_id, r.round_num, r.winning_team,
                   prs.team_id, prs.deaths, prs.kills, prs.economy_loadout_value
            FROM player_round_stats prs
            JOIN rounds r ON prs.round_id = r.id
            JOIN (
                SELECT m.match_id, m.started_at
                FROM player_match_stats pms
                JOIN matches m ON pms.match_id = m.match_id
                WHERE pms.puuid = %s {filter_str}
                ORDER BY m.started_at DESC
                LIMIT %s
            ) recent ON recent.match_id = r.match_id
            WHERE prs.puuid = %s
            ORDER BY recent.started_at, r.match_id, r.round_num
            """,
            [puuid] + params + [int(match_limit), puuid],
        )
        rows = cur.fetchall()
        if not rows:
            return None

        round_ids = [r["round_id"] for r in rows]
        placeholders = ",".join(["%s"] * len(round_ids))
        cur.execute(
            f"""
            SELECT round_id, killer_puuid, victim_puuid, time_in_round_ms,
                   is_opening_kill
            FROM kill_events
            WHERE round_id IN ({placeholders})
              AND (killer_puuid = %s OR victim_puuid = %s)
            """,
            round_ids + [puuid, puuid],
        )
        events = cur.fetchall()

    early_death_rounds: set[int] = set()
    opening: dict[int, bool] = {}  # round_id -> player won the opening duel
    for e in events:
        if e["victim_puuid"] == puuid and int(e["time_in_round_ms"]) < 15000:
            early_death_rounds.add(e["round_id"])
        if e["is_opening_kill"]:
            opening[e["round_id"]] = e["killer_puuid"] == puuid

    def _bucket():
        return {"rounds": 0, "wins": 0}

    pistol = _bucket()
    pistol_kills = 0
    pistol_deaths = 0
    post_pistol_win = _bucket()   # round right after a won pistol
    post_pistol_loss = _bucket()  # round right after a lost pistol
    after_win = _bucket()         # momentum: round after any won round
    after_loss = _bucket()        # bounce-back: round after any lost round
    sides = {
        "attack": {"rounds": 0, "wins": 0, "early_deaths": 0, "od_attempts": 0, "od_wins": 0},
        "defense": {"rounds": 0, "wins": 0, "early_deaths": 0, "od_attempts": 0, "od_wins": 0},
    }

    prev_match = None
    prev_won: bool | None = None
    prev_was_pistol_won: bool | None = None
    for r in rows:
        if r["match_id"] != prev_match:
            prev_match = r["match_id"]
            prev_won = None
            prev_was_pistol_won = None

        num = int(r["round_num"])
        won = r["winning_team"] == r["team_id"]
        side = "attack" if _attacking(r["team_id"], num) else "defense"

        s = sides[side]
        s["rounds"] += 1
        s["wins"] += won
        s["early_deaths"] += r["round_id"] in early_death_rounds
        if r["round_id"] in opening:
            s["od_attempts"] += 1
            s["od_wins"] += opening[r["round_id"]]

        if num in (0, 12):  # pistol rounds
            pistol["rounds"] += 1
            pistol["wins"] += won
            pistol_kills += int(r["kills"] or 0)
            pistol_deaths += int(r["deaths"] or 0)
        elif prev_was_pistol_won is not None:
            target = post_pistol_win if prev_was_pistol_won else post_pistol_loss
            target["rounds"] += 1
            target["wins"] += won

        if prev_won is not None:
            target = after_win if prev_won else after_loss
            target["rounds"] += 1
            target["wins"] += won

        prev_was_pistol_won = won if num in (0, 12) else None
        prev_won = won

    def _wr(b):
        return round(b["wins"] / b["rounds"] * 100, 1) if b["rounds"] else None

    matches_covered = len({r["match_id"] for r in rows})
    return {
        "matches_covered": matches_covered,
        "total_rounds": len(rows),
        "pistol": {
            "rounds": pistol["rounds"],
            "win_pct": _wr(pistol),
            "avg_kills": round(pistol_kills / pistol["rounds"], 2) if pistol["rounds"] else 0,
            "avg_deaths": round(pistol_deaths / pistol["rounds"], 2) if pistol["rounds"] else 0,
        },
        "post_pistol": {
            "after_win_pct": _wr(post_pistol_win),
            "after_loss_pct": _wr(post_pistol_loss),
        },
        "momentum": {
            "after_won_round_pct": _wr(after_win),
            "after_lost_round_pct": _wr(after_loss),
        },
        "sides": {
            side: {
                "win_pct": _wr({"rounds": s["rounds"], "wins": s["wins"]}),
                "rounds": s["rounds"],
                "early_death_pct": round(s["early_deaths"] / s["rounds"] * 100, 1) if s["rounds"] else None,
                "opening_duel_attempts": s["od_attempts"],
                "opening_duel_win_pct": round(s["od_wins"] / s["od_attempts"] * 100, 1) if s["od_attempts"] else None,
            }
            for side, s in sides.items()
        },
    }


# ── Opponent-strength context ────────────────────────────────────────────
# Raw ACS says nothing without knowing who the player faced. These queries
# supply that context so the coach can separate "the lobby was harder" from
# "you played worse".
#
# Scope note, measured on this DB: ranked matchmaking is tight — 86% of
# matches have the enemy team's average tier within ±1 step of the player's,
# and comparing each player against their own average shows lobby-average
# difficulty moves ACS by only a few points. So there is deliberately NO
# "expected ACS" model here; it would imply precision the data can't support.
# What does show a real effect is the single strongest opponent: avg ACS
# falls 220 -> 176 -> 130 as the best enemy goes from even-rank to +9 to +15.
# That asymmetry is why get_duel_strength_profile is the load-bearing query.
#
# tier_id is TINYINT UNSIGNED: every tier subtraction must CAST(... AS
# SIGNED) or MariaDB raises error 1690 the moment a delta goes negative.
# Tier numbering is Valorant's competitiveTier: 3=Iron 1 … 27=Radiant, so
# +3 is one full rank and +1 is one subtier.


def _tier_name(tier_id: int) -> str:
    """Render a competitiveTier number as its rank name."""
    if tier_id <= 2:
        return "Unranked"
    names = ("Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal")
    idx = (tier_id - 3) // 3
    if idx >= len(names):
        return "Radiant"
    return f"{names[idx]} {(tier_id - 3) % 3 + 1}"


def get_lobby_context(
    conn,
    puuid: str,
    match_limit: int = 20,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> list[dict] | None:
    """Per-match lobby strength for the player's recent matches.

    lobby_delta = avg enemy tier - player tier, in competitiveTier steps
    (+3 = enemies averaged one full rank above the player). Returns None when
    no match has usable tier data on both sides.
    """
    filter_str, params = _match_filters(game_modes, None)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT me.match_id, m.map_id, m.started_at, me.acs, me.won,
                   me.total_kills, me.total_deaths,
                   CAST(me.tier_id AS SIGNED)          AS player_tier,
                   AVG(CAST(en.tier_id AS SIGNED))     AS enemy_avg_tier,
                   MAX(CAST(en.tier_id AS SIGNED))     AS enemy_max_tier,
                   COUNT(en.id)                        AS enemies_tiered
            FROM player_match_stats me
            JOIN matches m ON m.match_id = me.match_id
            JOIN player_match_stats en
                 ON en.match_id = me.match_id
                AND en.team_id <> me.team_id
                AND en.tier_id > 0
            WHERE me.puuid = %s AND me.tier_id > 0 AND me.total_rounds >= 5 {filter_str}
            GROUP BY me.id, me.match_id, m.map_id, m.started_at, me.acs, me.won,
                     me.total_kills, me.total_deaths, me.tier_id
            ORDER BY m.started_at DESC
            LIMIT %s
            """,
            [puuid] + params + [int(match_limit)],
        )
        rows = list(reversed(cur.fetchall()))

    if not rows:
        return None

    out = []
    for r in rows:
        player_tier = int(r["player_tier"])
        enemy_avg = _f(r["enemy_avg_tier"]) or 0.0
        deaths = int(r["total_deaths"] or 0)
        started = r["started_at"]
        out.append(
            {
                "match_id": r["match_id"],
                "map": r["map_id"],
                "started_at": started.isoformat() if isinstance(started, datetime) else started,
                "acs": round(_f(r["acs"]) or 0, 1),
                "kd": round(int(r["total_kills"] or 0) / deaths, 2) if deaths else None,
                "won": bool(r["won"]),
                "player_tier": player_tier,
                "player_tier_name": _tier_name(player_tier),
                "enemy_avg_tier": round(enemy_avg, 2),
                "enemy_max_tier": int(r["enemy_max_tier"]),
                "enemy_max_tier_name": _tier_name(int(r["enemy_max_tier"])),
                "enemies_tiered": int(r["enemies_tiered"]),
                "lobby_delta": round(enemy_avg - player_tier, 2),
                # The strongest single opponent is the part that actually
                # moves the player's stat line.
                "toughest_enemy_edge": int(r["enemy_max_tier"]) - player_tier,
            }
        )
    return out


def detect_rank_transition(
    conn,
    puuid: str,
    match_limit: int = 40,
    calibration_window: int = 15,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """Most recent rank change and how the player has performed since.

    A promotion moves the player into a bracket where everyone is stronger, so
    raw ACS usually dips — against their own history that reads as a slump when
    it's really a harder pool. Reporting the change with before/after ACS lets
    the coach frame the dip as bracket adjustment.

    Only plausible transitions count: a jump of more than 3 subtiers between
    consecutive matches is a season reset or bad data, not a rank change.
    """
    lobby = get_lobby_context(conn, puuid, match_limit, game_modes)
    if not lobby:
        return None

    change_idx = next(
        (
            i
            for i in range(len(lobby) - 1, 0, -1)
            if lobby[i]["player_tier"] != lobby[i - 1]["player_tier"]
            and abs(lobby[i]["player_tier"] - lobby[i - 1]["player_tier"]) <= 3
        ),
        None,
    )
    if change_idx is None:
        return None

    before, after = lobby[:change_idx], lobby[change_idx:]
    from_tier = before[-1]["player_tier"]
    to_tier = after[0]["player_tier"]

    def _avg(rows, key):
        vals = [r[key] for r in rows if r[key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "direction": "promotion" if to_tier > from_tier else "demotion",
        "from_tier_name": _tier_name(from_tier),
        "to_tier_name": _tier_name(to_tier),
        "matches_since": len(after),
        "calibrating": len(after) <= calibration_window,
        "acs_before": _avg(before, "acs"),
        "acs_after": _avg(after, "acs"),
        "kd_before": _avg(before, "kd"),
        "kd_after": _avg(after, "kd"),
    }


def get_duel_strength_profile(
    conn,
    puuid: str,
    match_limit: int = 20,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """Kills and deaths split by the opponent's rank relative to the player.

    Dying repeatedly to someone several tiers above is lobby context, not a
    skill flaw; dying to lower-ranked opponents is the genuine red flag. Also
    surfaces the single opponent responsible for the most deaths, which is how
    one smurf can distort an entire match's stat line.
    """
    filter_str, params = _match_filters(game_modes, None)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT ke.killer_puuid, ke.victim_puuid, r.match_id,
                   CAST(kt.tier_id AS SIGNED) AS killer_tier,
                   CAST(vt.tier_id AS SIGNED) AS victim_tier,
                   opp.game_name AS opponent_name, opp.tag_line AS opponent_tag
            FROM kill_events ke
            JOIN rounds r ON r.id = ke.round_id
            JOIN (
                SELECT m.match_id
                FROM player_match_stats pms
                JOIN matches m ON m.match_id = pms.match_id
                WHERE pms.puuid = %s AND pms.tier_id > 0 AND pms.total_rounds >= 5 {filter_str}
                ORDER BY m.started_at DESC
                LIMIT %s
            ) recent ON recent.match_id = r.match_id
            JOIN player_match_stats kt ON kt.match_id = r.match_id AND kt.puuid = ke.killer_puuid
            JOIN player_match_stats vt ON vt.match_id = r.match_id AND vt.puuid = ke.victim_puuid
            JOIN players opp
                 ON opp.puuid = IF(ke.killer_puuid = %s, ke.victim_puuid, ke.killer_puuid)
            WHERE (ke.killer_puuid = %s OR ke.victim_puuid = %s)
              AND kt.tier_id > 0 AND vt.tier_id > 0
            """,
            [puuid] + params + [int(match_limit), puuid, puuid, puuid],
        )
        rows = cur.fetchall()

    if not rows:
        return None

    kills = {"vs_stronger": 0, "vs_even": 0, "vs_weaker": 0}
    deaths = {"to_stronger": 0, "to_even": 0, "to_weaker": 0}
    deaths_by_opponent: dict[tuple, dict] = {}

    for r in rows:
        is_kill = r["killer_puuid"] == puuid
        # Positive edge = the opponent outranks the player.
        edge = (
            int(r["victim_tier"]) - int(r["killer_tier"])
            if is_kill
            else int(r["killer_tier"]) - int(r["victim_tier"])
        )
        band = "stronger" if edge >= 2 else ("weaker" if edge <= -2 else "even")
        if is_kill:
            kills[f"vs_{band}"] += 1
        else:
            deaths[f"to_{band}"] += 1
            key = (r["opponent_name"], r["opponent_tag"])
            slot = deaths_by_opponent.setdefault(key, {"deaths": 0, "tier_edge": edge})
            slot["deaths"] += 1
            # Keep the largest edge seen: an opponent who outranks the player
            # is the headline, not whichever duel happened to come first.
            slot["tier_edge"] = max(slot["tier_edge"], edge)

    total_deaths = sum(deaths.values())
    total_kills = sum(kills.values())
    top = max(deaths_by_opponent.items(), key=lambda kv: kv[1]["deaths"], default=None)

    result = {
        "matches_covered": len({r["match_id"] for r in rows}),
        "kills": {**kills, "total": total_kills},
        "deaths": {**deaths, "total": total_deaths},
        "deaths_to_stronger_pct": round(deaths["to_stronger"] / total_deaths * 100, 1) if total_deaths else None,
        "deaths_to_weaker_pct": round(deaths["to_weaker"] / total_deaths * 100, 1) if total_deaths else None,
        "kills_vs_stronger_pct": round(kills["vs_stronger"] / total_kills * 100, 1) if total_kills else None,
        "nemesis": None,
    }
    # Only call out a nemesis when one opponent is a meaningful share of deaths.
    if top and total_deaths and top[1]["deaths"] >= max(3, total_deaths * 0.15):
        (name, tag), info = top
        result["nemesis"] = {
            "name": f"{name}#{tag}",
            "deaths": info["deaths"],
            "share_pct": round(info["deaths"] / total_deaths * 100, 1),
            "tier_edge": info["tier_edge"],
        }
    return result


# ── OneTap Rating (OTR) ──────────────────────────────────────────────────
# One number for "did you outplay the people in front of you". Each pillar
# is a z-score against the OTHER 9 players in the same lobby, which makes
# the score rank-, map- and smurf-adjusted by construction: topping a Bronze
# lobby scores the same as topping an Immortal lobby.
#
# Pillars and weights are empirical, not aesthetic (measured on this DB by
# comparing lobby top-2 vs bottom-5, and won vs lost rounds):
#   damage/round   0.45  — the engine: 207 vs 133 dmg/round top-2 vs rest
#   survival       0.25  — 52.9% survival in won rounds vs 1.3% in lost
#   impact         0.20  — opening kills + multikill rounds
#   precision      0.10  — headshot rate; real but most lobby-dependent
# Trades and early deaths were tested and rejected: both are flat or
# inverted across ranks (Immortals die early MORE than Bronze — deliberate
# aggression), so rewarding them would coach players downward.
#
# Validation (7,350 player-matches): AUC predicting the match win — OTR
# 0.743 vs ACS-percentile 0.592. Monotonic: OTR 33 → 4.5% win rate,
# 50 → 51%, 69 → 94%. Single-match SD ≈ 8 points; rolling-10 noise band
# ≈ ±2.6 — treat trend moves inside ±3 as noise.
OTR_WEIGHTS = {"damage": 0.45, "survival": 0.25, "impact": 0.20, "precision": 0.10}
OTR_SCALE = 12.0  # z-units → points; 50 = lobby average
OTR_NOISE_BAND = 3.0  # rolling-10 moves inside ±this are noise
OTR_WINDOW = 10

_OTR_MATCH_SQL = """
WITH pm AS (
    SELECT r.match_id, prs.puuid,
           SUM(prs.damage_dealt) / COUNT(*)                  AS dmg_pr,
           AVG(prs.deaths = 0)                               AS surv,
           MAX(pms.headshot_pct)                             AS hs,
           SUM(prs.kills >= 2) / COUNT(*)                    AS multi,
           SUM(EXISTS(
               SELECT 1 FROM kill_events ke
               WHERE ke.round_id = r.id
                 AND ke.killer_puuid = prs.puuid
                 AND ke.is_opening_kill
           )) / COUNT(*)                                     AS ok_rate,
           MAX(pms.won)                                      AS won,
           MAX(pms.acs)                                      AS acs
    FROM player_round_stats prs
    JOIN rounds r  ON r.id = prs.round_id
    JOIN matches m ON m.match_id = r.match_id
    JOIN player_match_stats pms
         ON pms.match_id = r.match_id AND pms.puuid = prs.puuid
    WHERE m.game_mode IN ({modes}) AND pms.total_rounds >= 5
    GROUP BY r.match_id, prs.puuid
)
SELECT match_id, puuid, won, acs,
       COALESCE((dmg_pr - AVG(dmg_pr) OVER w) / NULLIF(STDDEV_POP(dmg_pr) OVER w, 0), 0) AS z_damage,
       COALESCE((surv   - AVG(surv)   OVER w) / NULLIF(STDDEV_POP(surv)   OVER w, 0), 0) AS z_survival,
       COALESCE(((multi + ok_rate) - AVG(multi + ok_rate) OVER w)
                / NULLIF(STDDEV_POP(multi + ok_rate) OVER w, 0), 0)                      AS z_impact,
       COALESCE((hs - AVG(hs) OVER w) / NULLIF(STDDEV_POP(hs) OVER w, 0), 0)             AS z_precision
FROM pm
WINDOW w AS (PARTITION BY match_id)
"""


def _otr_from_z(z: dict) -> float:
    return 50.0 + OTR_SCALE * sum(OTR_WEIGHTS[p] * z[p] for p in OTR_WEIGHTS)


def _pillar_score(zval: float) -> int:
    """Map a lobby z-score to a 0-100 pillar display score (50 = lobby avg)."""
    return int(max(0, min(100, round(50 + 16 * zval))))


def get_otr_profile(
    conn,
    puuid: str,
    match_limit: int = 30,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """OneTap Rating over the player's recent matches.

    Returns per-match OTR + pillar breakdown (chronological), the rolling
    OTR_WINDOW headline, a trend verdict gated on the noise band, and the
    weakest pillar. None when the player has no scored ranked matches.
    """
    modes = game_modes or RANKED_MODES
    placeholders = ",".join(["%s"] * len(modes))
    sql = f"""
        SELECT z.*, m.map_id, m.started_at
        FROM ({_OTR_MATCH_SQL.format(modes=placeholders)}) z
        JOIN matches m ON m.match_id = z.match_id
        WHERE z.puuid = %s
        ORDER BY m.started_at DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, list(modes) + [puuid, int(match_limit)])
        rows = list(reversed(cur.fetchall()))
    if not rows:
        return None

    matches = []
    for r in rows:
        z = {p: float(r[f"z_{p}"]) for p in OTR_WEIGHTS}
        started = r["started_at"]
        matches.append(
            {
                "match_id": r["match_id"],
                "map": r["map_id"],
                "started_at": started.isoformat() if isinstance(started, datetime) else started,
                "won": bool(r["won"]),
                "acs": round(_f(r["acs"]) or 0, 1),
                "otr": round(_otr_from_z(z), 1),
                "pillars": {p: _pillar_score(z[p]) for p in OTR_WEIGHTS},
            }
        )

    otrs = [m["otr"] for m in matches]
    current = round(sum(otrs[-OTR_WINDOW:]) / len(otrs[-OTR_WINDOW:]), 1)
    previous = None
    if len(otrs) >= OTR_WINDOW + 5:
        prev_slice = otrs[-2 * OTR_WINDOW : -OTR_WINDOW] or otrs[: -OTR_WINDOW]
        previous = round(sum(prev_slice) / len(prev_slice), 1)

    trend = "flat"
    if previous is not None:
        delta = current - previous
        if delta > OTR_NOISE_BAND:
            trend = "improving"
        elif delta < -OTR_NOISE_BAND:
            trend = "declining"

    # Pillar averages over the current window drive the mission.
    window = matches[-OTR_WINDOW:]
    pillar_avg = {
        p: round(sum(m["pillars"][p] for m in window) / len(window)) for p in OTR_WEIGHTS
    }
    weakest = min(pillar_avg, key=pillar_avg.get)

    return {
        "matches_scored": len(matches),
        "matches": matches,
        "otr": current,
        "otr_previous": previous,
        "trend": trend,
        "noise_band": OTR_NOISE_BAND,
        "pillars": pillar_avg,
        "weakest_pillar": weakest,
    }


def get_otr_percentile(
    conn,
    puuid: str,
    otr: float,
    game_modes: Sequence[str] | None = RANKED_MODES,
) -> dict | None:
    """Where the player's rolling OTR sits among same-rank players in our DB.

    Cohort = per-player mean OTR of everyone whose latest tier is within one
    full rank (±3 subtiers). Returns None when the cohort is too small to be
    meaningful (fewer than 20 players).
    """
    modes = game_modes or RANKED_MODES
    placeholders = ",".join(["%s"] * len(modes))
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT CAST(pms.tier_id AS SIGNED) AS tier
            FROM player_match_stats pms
            JOIN matches m ON m.match_id = pms.match_id
            WHERE pms.puuid = %s AND pms.tier_id > 0
            ORDER BY m.started_at DESC LIMIT 1
            """,
            (puuid,),
        )
        row = cur.fetchone()
        if not row:
            return None
        tier = int(row["tier"])

        cur.execute(
            f"""
            SELECT z.puuid,
                   AVG(50 + %s * (0.45 * z.z_damage + 0.25 * z.z_survival
                                  + 0.20 * z.z_impact + 0.10 * z.z_precision)) AS mean_otr
            FROM ({_OTR_MATCH_SQL.format(modes=placeholders)}) z
            JOIN (
                SELECT pms.puuid, CAST(pms.tier_id AS SIGNED) AS tier,
                       ROW_NUMBER() OVER (PARTITION BY pms.puuid ORDER BY m.started_at DESC) rn
                FROM player_match_stats pms
                JOIN matches m ON m.match_id = pms.match_id
                WHERE pms.tier_id > 0
            ) lt ON lt.puuid = z.puuid AND lt.rn = 1
                AND lt.tier BETWEEN %s AND %s
            GROUP BY z.puuid
            HAVING COUNT(*) >= 3
            """,
            [OTR_SCALE] + list(modes) + [tier - 3, tier + 3],
        )
        cohort = [float(r["mean_otr"]) for r in cur.fetchall()]

    if len(cohort) < 20:
        return None
    below = sum(1 for v in cohort if v < otr)
    return {
        "percentile": round(below / len(cohort) * 100),
        "cohort_size": len(cohort),
        "cohort_rank_name": _tier_name(tier),
    }


# ── Missions: assigned, played, GRADED ───────────────────────────────────
# A mission is a checkable contract: "lift your weakest pillar to <target>
# average over your next N ranked matches". It persists in player_missions,
# fills a progress bar as matches land, resolves to completed/failed at N
# matches, and immediately assigns the next one. The graded metric is the
# lobby-relative pillar score (not a raw stat), so a mission can't be
# completed or failed by lobby luck.
_PILLAR_MISSIONS = {
    "damage": {
        "title": "Raise your damage output",
        "why": "Damage per round is the single biggest gap between lobby-topping players and the rest (207 vs 133 per round).",
        "how": "Fire at every viable target even when you don't get the kill — chip damage sets up your team. Stop saving when a rifle fight is winnable.",
    },
    "survival": {
        "title": "Live past the fight",
        "why": "Players survive 53% of rounds they win and 1% of rounds they lose — staying alive IS winning.",
        "how": "After getting a kill, reposition instead of holding the same angle. When you're last alive on a lost round, save the weapon.",
    },
    "impact": {
        "title": "Create round-swinging moments",
        "why": "Opening kills and multikill rounds decide rounds more than steady trading.",
        "how": "Coordinate your entry with utility — swing when the flash pops, not after. On defense, take one confident first contact instead of waiting.",
    },
    "precision": {
        "title": "Sharpen your first bullet",
        "why": "Lobby-topping players hold ~32% headshots vs ~29% for the rest — small edge, every fight.",
        "how": "Crosshair at head level while moving through the map, always. 10 minutes of Deathmatch aiming ONLY for heads before ranked.",
    },
}

_MISSIONS_DDL = """
CREATE TABLE IF NOT EXISTS player_missions (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    puuid           CHAR(78)        NOT NULL,
    pillar          VARCHAR(12)     NOT NULL,
    baseline_score  TINYINT UNSIGNED NOT NULL,
    target_score    TINYINT UNSIGNED NOT NULL,
    target_matches  TINYINT UNSIGNED NOT NULL DEFAULT 5,
    assigned_after  TIMESTAMP       NOT NULL COMMENT 'grade matches started after this',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('active','completed','failed') NOT NULL DEFAULT 'active',
    resolved_at     TIMESTAMP       NULL,
    final_score     TINYINT UNSIGNED NULL,
    PRIMARY KEY (id),
    INDEX idx_pm_player (puuid, status, created_at)
) ENGINE=InnoDB
"""


def _mission_target(baseline: int) -> int:
    """Personalized, reachable target: +4 pillar points, kept inside a sane
    band so weak starts aren't demoralizing and strong starts stay earnable."""
    return max(48, min(68, baseline + 4))


def _assign_mission(cur, puuid: str, otr_profile: dict, target_matches: int) -> None:
    weakest = otr_profile["weakest_pillar"]
    baseline = int(otr_profile["pillars"][weakest])
    last_played = otr_profile["matches"][-1]["started_at"] if otr_profile["matches"] else None
    cur.execute(
        """
        INSERT INTO player_missions
            (puuid, pillar, baseline_score, target_score, target_matches, assigned_after)
        VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()))
        """,
        (puuid, weakest, baseline, _mission_target(baseline), target_matches, last_played),
    )


def _mission_payload(row: dict, window: list[dict]) -> dict:
    pillar = row["pillar"]
    t = _PILLAR_MISSIONS.get(pillar, {})
    current = (
        round(sum(m["pillars"][pillar] for m in window) / len(window))
        if window else None
    )
    return {
        "pillar": pillar,
        "title": t.get("title", pillar),
        "why": t.get("why", ""),
        "how": t.get("how", ""),
        "goal": (
            f"Lift your {pillar} pillar to a {int(row['target_score'])}+ average "
            f"over your next {int(row['target_matches'])} ranked matches"
        ),
        "baseline": int(row["baseline_score"]),
        "target": int(row["target_score"]),
        "target_matches": int(row["target_matches"]),
        "matches_played": len(window),
        "current_score": current,
        "on_track": current is not None and current >= int(row["target_score"]),
        "status": row["status"],
    }


def get_mission_state(
    conn,
    puuid: str,
    otr_profile: dict,
    target_matches: int = 5,
) -> dict | None:
    """The mission loop: assign → track → grade → celebrate → reassign.

    Returns {"active": <mission>, "last_resolved": <mission|None>,
    "stats": {completed, failed, streak}}. Idempotent per call; resolution
    happens the first time enough post-assignment matches exist.
    """
    if not otr_profile or not otr_profile.get("matches"):
        return None

    matches = otr_profile["matches"]  # chronological, ISO started_at

    with conn.cursor() as cur:
        cur.execute(_MISSIONS_DDL)

        cur.execute(
            "SELECT * FROM player_missions WHERE puuid = %s AND status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (puuid,),
        )
        active = cur.fetchone()

        if not active:
            _assign_mission(cur, puuid, otr_profile, target_matches)
            conn.commit()
            cur.execute(
                "SELECT * FROM player_missions WHERE puuid = %s AND status = 'active' "
                "ORDER BY created_at DESC LIMIT 1",
                (puuid,),
            )
            active = cur.fetchone()

        # Matches that count toward this mission: started after assignment.
        cutoff = active["assigned_after"]
        cutoff_iso = cutoff.isoformat() if isinstance(cutoff, datetime) else str(cutoff)
        window = [m for m in matches if str(m["started_at"]) > cutoff_iso]
        window = window[: int(active["target_matches"])]

        last_resolved = None
        if len(window) >= int(active["target_matches"]):
            pillar = active["pillar"]
            final = round(sum(m["pillars"][pillar] for m in window) / len(window))
            status = "completed" if final >= int(active["target_score"]) else "failed"
            cur.execute(
                "UPDATE player_missions SET status = %s, final_score = %s, resolved_at = NOW() "
                "WHERE id = %s",
                (status, final, active["id"]),
            )
            last_resolved = _mission_payload({**active, "status": status}, window)
            last_resolved["final_score"] = final
            _assign_mission(cur, puuid, otr_profile, target_matches)
            conn.commit()
            cur.execute(
                "SELECT * FROM player_missions WHERE puuid = %s AND status = 'active' "
                "ORDER BY created_at DESC LIMIT 1",
                (puuid,),
            )
            active = cur.fetchone()
            window = []
        else:
            # Surface the most recent resolution once more if it's fresh (the
            # player may not have seen it yet); frontend decides how to show it.
            cur.execute(
                "SELECT * FROM player_missions WHERE puuid = %s AND status != 'active' "
                "AND resolved_at >= NOW() - INTERVAL 2 DAY "
                "ORDER BY resolved_at DESC LIMIT 1",
                (puuid,),
            )
            recent = cur.fetchone()
            if recent:
                last_resolved = _mission_payload(recent, [])
                last_resolved["final_score"] = (
                    int(recent["final_score"]) if recent["final_score"] is not None else None
                )

        # Identity stats: what the player has accumulated.
        cur.execute(
            "SELECT status, COUNT(*) n FROM player_missions "
            "WHERE puuid = %s AND status != 'active' GROUP BY status",
            (puuid,),
        )
        counts = {r["status"]: int(r["n"]) for r in cur.fetchall()}
        cur.execute(
            "SELECT status FROM player_missions WHERE puuid = %s AND status != 'active' "
            "ORDER BY resolved_at DESC LIMIT 20",
            (puuid,),
        )
        streak = 0
        for r in cur.fetchall():
            if r["status"] == "completed":
                streak += 1
            else:
                break

    return {
        "active": _mission_payload(active, window),
        "last_resolved": last_resolved,
        "stats": {
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "streak": streak,
        },
    }


def build_weekly_recap(otr_profile: dict, transition: dict | None = None) -> dict | None:
    """Shareable recap over the last OTR window vs the one before it.

    Returns None until there are enough matches for a before/after story.
    """
    if otr_profile.get("otr_previous") is None:
        return None
    matches = otr_profile["matches"]
    window = matches[-OTR_WINDOW:]
    prev = matches[-2 * OTR_WINDOW : -OTR_WINDOW] or matches[:-OTR_WINDOW]

    def _pillar_delta(p):
        cur = sum(m["pillars"][p] for m in window) / len(window)
        old = sum(m["pillars"][p] for m in prev) / len(prev)
        return round(cur - old, 1)

    deltas = {p: _pillar_delta(p) for p in OTR_WEIGHTS}
    best = max(deltas, key=deltas.get)
    wins = sum(1 for m in window if m["won"])
    recap = {
        "otr": otr_profile["otr"],
        "otr_delta": round(otr_profile["otr"] - otr_profile["otr_previous"], 1),
        "trend": otr_profile["trend"],
        "record": f"{wins}W-{len(window) - wins}L",
        "best_pillar_gain": {"pillar": best, "delta": deltas[best]} if deltas[best] > 0 else None,
        "best_match": max(window, key=lambda m: m["otr"]),
    }
    if transition:
        recap["rank_change"] = (
            f"{transition['from_tier_name']} → {transition['to_tier_name']}"
        )
    return recap
