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


def _attacking(team: str, round_num: int) -> bool:
    # Same side convention as get_side_bias: Red attacks rounds 0-11,
    # Blue rounds 12-23, overtime alternates starting with Red on even.
    if round_num < 12:
        return team == "Red"
    if round_num < 24:
        return team == "Blue"
    return (team == "Red") if (round_num % 2 == 0) else (team == "Blue")


def get_match_rounds(conn, match_id: str, puuid: str) -> list[dict]:
    """Round-by-round view of one match from the player's perspective.

    Feeds the coach LLM prompt: per round — result, side, player K/D/A,
    damage, loadout economy class, opening duel involvement, plant/defuse.
    """
    with conn.cursor() as cur:
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
                "side": "attack" if _attacking(team, num) else "defense",
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
