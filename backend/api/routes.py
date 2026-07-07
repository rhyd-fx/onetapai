import os
import sys

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make sibling packages (config, ingestion, analysis, api) importable regardless
# of working directory (temporary shim until the backend is packaged).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
from ingestion.etl import get_db_connection, process_match
from ingestion.worker import HenrikAPIClient
from analysis.mechanical.aim_profiler import AimProfile
from analysis.spatial import coordinates
from analysis.mental.tilt_detector import detect_tilt
from dataclasses import asdict
from api.queries import (
    resolve_puuid,
    get_player_summary,
    get_acs_trajectory,
    get_engagement_locations,
    get_map_coord_samples,
    get_match_timeline,
    get_telemetry,
    record_feedback,
    get_top_maps,
    get_top_weapons,
    get_aim_by_distance,
    get_economy_efficiency,
    get_side_bias,
    get_hardware_check,
    get_player_seasons,
    get_matchup_diagnostics,
    get_economy_split,
)
from api.auth_utils import hash_password, verify_password, generate_jwt, verify_jwt
from rag.retriever import CoachingRetriever
from rag.prompt_builder import build_coaching_prompt
from rag import llm

# Lazily-built retriever (loads the embedding model + Qdrant client once).
_retriever: CoachingRetriever | None = None


def _get_retriever() -> CoachingRetriever:
    global _retriever
    if _retriever is None:
        _retriever = CoachingRetriever.from_config()
    return _retriever


def _profile_for_prompt(summary: dict | None, aim: dict, telemetry: dict | None = None, matchup: dict | None = None) -> dict:
    """Shape a DB player summary into the dict build_coaching_prompt expects."""
    if not summary:
        return {}
    res = {
        "game_name": summary.get("game_name", ""),
        "tag_line": summary.get("tag_line", ""),
        "main_agent": summary.get("main_agent") or "Unknown",
        "avg_acs": summary.get("avg_acs") or 0,
        "headshot_pct": (summary.get("headshot_pct") or 0) * 100,
        "bodyshot_pct": (summary.get("bodyshot_pct") or 0) * 100,
        "issues": aim.get("deficiencies", []) if aim.get("available") else [],
    }
    if telemetry:
        res["opening_duel_wr"] = telemetry.get("opening_duel_win_pct") or 0
        res["zero_dmg_death_pct"] = telemetry.get("movement_error_pct") or 0
    if matchup:
        res["killer_roles"] = matchup.get("killer_roles") or {}
        res["utility_deaths"] = matchup.get("utility_deaths") or []
        res["utility_deaths_count"] = matchup.get("utility_deaths_count") or 0
        res["gun_deaths_count"] = matchup.get("gun_deaths_count") or 0
    return res

app = FastAPI(title="OneTap AI", version="1.0.0")

# CORS for the Next.js frontend (origins from config/.env).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _init_auth_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                username        VARCHAR(100)    NOT NULL UNIQUE,
                email           VARCHAR(100)    NOT NULL UNIQUE,
                password_hash   VARCHAR(255)    NOT NULL,
                created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB
            """)
            conn.commit()
            
            # Alter table to add linked_riot_id safely
            try:
                cur.execute("ALTER TABLE users ADD COLUMN linked_riot_id VARCHAR(100) NULL")
                conn.commit()
            except Exception:
                pass

            # Create search_history table for private search tracking
            cur.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                user_id         BIGINT UNSIGNED NOT NULL,
                riot_id         VARCHAR(100)    NOT NULL,
                searched_at     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uq_user_riot (user_id, riot_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """)
            conn.commit()

            # Create index for optimized search history query sorting
            try:
                cur.execute("CREATE INDEX idx_sh_user_time ON search_history (user_id, searched_at)")
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        print(f"Error initializing user DB: {e}")
    finally:
        conn.close()

# Run DDL initialization
_init_auth_db()


# --- Request/Response Models ---

class AnalysisRequest(BaseModel):
    riot_id: str                    # "PlayerName#TAG"
    region: str = "na"
    match_count: int = 20           # How many recent matches to analyze
    season_id: str | None = None
    competitive_only: bool = True
    skip_sync: bool = False


class CoachingQuestion(BaseModel):
    riot_id: str
    question: str
    context_match_ids: list[str] | None = None


class CoachingResponse(BaseModel):
    answer: str
    sources_used: list[dict]
    player_stats_referenced: dict
    follow_up_suggestions: list[str]


class FeedbackRequest(BaseModel):
    question: str
    rating: int                        # 1 = thumbs up, -1 = thumbs down
    riot_id: str | None = None
    answer_excerpt: str | None = None
    sources: list[dict] | None = None


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


# --- Auth Dependency ---

def get_current_user(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication token is missing or invalid. Please register or log in to use OneTap AI."
        )
    token = authorization.split(" ")[1]
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Your session has expired. Please log in again."
        )
    return payload


# --- Helpers ---

def _split_riot_id(riot_id: str) -> tuple[str, str]:
    if "#" not in riot_id:
        raise HTTPException(status_code=400, detail="riot_id must be 'Name#Tag'.")
    name, tag = riot_id.rsplit("#", 1)
    name, tag = name.strip(), tag.strip()
    if not name or not tag:
        raise HTTPException(status_code=400, detail="riot_id must be 'Name#Tag'.")
    return name, tag


def _connect():
    try:
        return get_db_connection()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


def _build_aim_profile(summary: dict, telemetry: dict | None = None, aim_by_distance: list[dict] | None = None) -> dict:
    """Run the mechanical AimProfile classifier on aggregate hit stats using telemetry and range stats."""
    hs = summary.get("headshot_pct")
    bs = summary.get("bodyshot_pct")
    ls = summary.get("legshot_pct")
    if hs is None or bs is None:
        return {"available": False, "reason": "no hit-distribution data yet"}

    hs_short = hs
    hs_long = hs
    if aim_by_distance:
        close_stats = next((a for a in aim_by_distance if a["range"] == "close"), None)
        long_stats = next((a for a in aim_by_distance if a["range"] == "long"), None)
        if close_stats:
            hs_short = (close_stats.get("headshot_pct") or 0.0) / 100
        if long_stats:
            hs_long = (long_stats.get("headshot_pct") or 0.0) / 100

    zero_dmg_pct = 0.0
    if telemetry and telemetry.get("movement_error_pct") is not None:
        zero_dmg_pct = telemetry["movement_error_pct"] / 100

    profile = AimProfile.from_db_stats(
        {
            "headshot_pct": hs,
            "bodyshot_pct": bs,
            "legshot_pct": ls or 0.0,
            "zero_damage_death_pct": zero_dmg_pct,
            "hs_by_range": {"short": hs_short, "long": hs_long},
            "bs_by_econ": {},
            "opening_hs_pct": 0.0,
        }
    )
    return {
        "available": True,
        "headshot_pct": profile.headshot_pct,
        "bodyshot_pct": profile.bodyshot_pct,
        "legshot_pct": profile.legshot_pct,
        "deficiencies": [d.value for d in profile.deficiencies],
    }


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/register")
async def auth_register(req: RegisterRequest):
    username = req.username.strip()
    email = req.email.strip().lower()
    password = req.password
    
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
        
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username or email is already registered.")
            
            pwd_hash = hash_password(password)
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, pwd_hash)
            )
            conn.commit()
    finally:
        conn.close()
        
    return {"success": True, "message": "User registered successfully."}


@app.post("/api/v1/auth/login")
async def auth_login(req: LoginRequest):
    user_input = req.username_or_email.strip()
    password = req.password
    
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = %s OR email = %s",
                (user_input, user_input)
            )
            user = cur.fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid username or password.")
                
            token = generate_jwt({
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"]
            })
            
            return {
                "token": token,
                "username": user["username"]
            }
    finally:
        conn.close()


@app.get("/api/v1/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email, linked_riot_id FROM users WHERE id = %s", (user.get("user_id"),))
            db_user = cur.fetchone()
            if db_user:
                return {
                    "user_id": db_user["id"],
                    "username": db_user["username"],
                    "email": db_user["email"],
                    "linked_riot_id": db_user["linked_riot_id"]
                }
    except Exception:
        pass
    finally:
        conn.close()
        
    return {
        "user_id": user.get("user_id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "linked_riot_id": None
    }


@app.get("/api/v1/auth/recent-searches")
async def get_recent_searches(user: dict = Depends(get_current_user)):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT riot_id FROM search_history WHERE user_id = %s ORDER BY searched_at DESC LIMIT 5",
                (user.get("user_id"),)
            )
            rows = cur.fetchall()
            return [r["riot_id"] for r in rows]
    except Exception as e:
        print(f"Error fetching search history: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve search history.")
    finally:
        conn.close()


async def _sync_from_henrik(name: str, tag: str, region: str, size: int) -> dict:
    """Fetch the player's recent matches from Henrik and ingest any new ones.

    Best-effort: never raises. Returns {fetched, ingested, error} so analysis can
    still run on whatever is already in the DB if the live fetch fails.
    """
    status: dict = {"fetched": 0, "ingested": 0, "error": None}
    try:
        client = HenrikAPIClient.from_config()  # requires HENRIK_API_KEY
    except Exception as e:  # noqa: BLE001
        status["error"] = f"Henrik client unavailable: {e}"
        return status

    matches: list[dict] = []
    try:
        # Resolve the account's true region when possible (user-picked region
        # may be wrong); fall back to the provided region on any failure.
        try:
            acct = await client.get_account(name, tag)
            region = acct.get("region") or region
            if acct:
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO players (puuid, game_name, tag_line, region, card_uuid)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                game_name = VALUES(game_name),
                                tag_line = VALUES(tag_line),
                                region = VALUES(region),
                                card_uuid = VALUES(card_uuid)
                        """, (
                            acct.get("puuid"),
                            acct.get("name", name),
                            acct.get("tag", tag),
                            acct.get("region", region),
                            acct.get("card", {}).get("id")
                        ))
                    conn.commit()
                finally:
                    conn.close()
        except Exception:  # noqa: BLE001
            pass
        matches = await client.get_matches(region, name, tag, size=size)
        status["fetched"] = len(matches)
    except Exception as e:  # noqa: BLE001
        status["error"] = f"Henrik fetch failed: {e}"
    finally:
        await client.close()

    if not matches:
        return status

    # Ingest only matches not already stored (re-processing would duplicate
    # kill_events, which has no unique key).
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT match_id FROM matches")
            existing = {r["match_id"] for r in cur.fetchall()}
        for m in matches:
            mid = (m.get("metadata") or {}).get("matchid")
            if not mid or mid in existing:
                continue
            try:
                process_match(m, conn)  # commits per match
                status["ingested"] += 1
            except Exception as e:  # noqa: BLE001
                print(f"  ! ETL failed for {mid}: {e}")
    finally:
        conn.close()
    return status


@app.post("/api/v1/analyze")
async def analyze_player(req: AnalysisRequest, user: dict = Depends(get_current_user)):
    """Fetch the player's recent matches live from Henrik, ingest new ones, then
    analyze: identity + aggregate stats, mechanical aim profile, ACS trajectory."""
    name, tag = _split_riot_id(req.riot_id)

    # Henrik v3 caps full-match batches; keep the live pull modest.
    if req.skip_sync:
        sync = {"fetched": 0, "ingested": 0, "error": None}
    else:
        sync = await _sync_from_henrik(name, tag, req.region, size=min(req.match_count, 10))

    conn = _connect()
    try:
        puuid = resolve_puuid(conn, name, tag)
        if not puuid:
            detail = f"No data found for {req.riot_id}."
            if sync.get("error"):
                detail += f" ({sync['error']})"
            else:
                detail += " Check the Riot ID and region."
            raise HTTPException(status_code=404, detail=detail)
            
        # Automatically link Riot ID on first successful search and track search history
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT linked_riot_id FROM users WHERE id = %s", (user.get("user_id"),))
                db_u = cur.fetchone()
                if db_u and not db_u.get("linked_riot_id"):
                    cur.execute("UPDATE users SET linked_riot_id = %s WHERE id = %s", (req.riot_id, user.get("user_id")))
                
                # Log search history entry
                cur.execute("""
                    INSERT INTO search_history (user_id, riot_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE searched_at = CURRENT_TIMESTAMP
                """, (user.get("user_id"), req.riot_id))

                # Optimize: prune history beyond top 10 rows to prevent database bloat
                cur.execute("""
                    DELETE FROM search_history 
                    WHERE user_id = %s 
                      AND id NOT IN (
                          SELECT id FROM (
                              SELECT id FROM search_history 
                              WHERE user_id = %s 
                              ORDER BY searched_at DESC 
                              LIMIT 10
                          ) tmp
                      )
                """, (user.get("user_id"), user.get("user_id")))
                conn.commit()
        except Exception as e:
            print(f"Error updating user profile history: {e}")

        summary = get_player_summary(conn, puuid, req.season_id, req.competitive_only)
        trajectory = get_acs_trajectory(conn, puuid, limit=req.match_count, season_id=req.season_id, competitive_only=req.competitive_only)
        telemetry = get_telemetry(conn, puuid, req.season_id, req.competitive_only)
        top_maps = get_top_maps(conn, puuid, req.season_id, req.competitive_only)
        top_weapons = get_top_weapons(conn, puuid, req.season_id, req.competitive_only)
        aim_by_distance = get_aim_by_distance(conn, puuid, req.season_id, req.competitive_only)
        economy_efficiency = get_economy_efficiency(conn, puuid, req.season_id, req.competitive_only)
        side_bias = get_side_bias(conn, puuid, req.season_id, req.competitive_only)
        hardware_check = get_hardware_check(conn, puuid)
        seasons = get_player_seasons(conn, puuid)
        matchup_diagnostics = get_matchup_diagnostics(conn, puuid, req.season_id, req.competitive_only)
        economy_split = get_economy_split(conn, puuid, req.season_id, req.competitive_only)
    finally:
        conn.close()

    return {
        "player_profile": summary,
        "aim_profile": _build_aim_profile(summary, telemetry, aim_by_distance),
        "acs_trajectory": trajectory,
        "telemetry": telemetry,
        "top_maps": top_maps,
        "top_weapons": top_weapons,
        "aim_by_distance": aim_by_distance,
        "economy_efficiency": economy_efficiency,
        "side_bias": side_bias,
        "hardware_check": hardware_check,
        "seasons": seasons,
        "matchup_diagnostics": matchup_diagnostics,
        "economy_split": economy_split,
        "sync": sync,
    }


@app.get("/api/v1/player/{riot_id}/acs-trajectory")
async def acs_trajectory(riot_id: str, last_n: int = 20, user: dict = Depends(get_current_user)):
    """Match-by-match ACS for tilt visualization."""
    name, tag = _split_riot_id(riot_id)
    conn = _connect()
    try:
        puuid = resolve_puuid(conn, name, tag)
        if not puuid:
            raise HTTPException(status_code=404, detail=f"No ingested data for {riot_id}.")
        return {"trajectory": get_acs_trajectory(conn, puuid, limit=last_n)}
    finally:
        conn.close()


# --- Not yet wired (stubs kept so the contract is visible) ---

@app.post("/api/v1/coach", response_model=CoachingResponse)
async def coaching_chat(req: CoachingQuestion, user: dict = Depends(get_current_user)):
    """RAG-powered coaching Q&A: retrieve relevant knowledge, ground it in the
    player's stats (when available), and generate a response via OpenRouter."""
    # Player context is optional — a general question still works. DB failure
    # here is non-fatal; we just answer without personalized stats.
    profile: dict = {}
    if "#" in req.riot_id:
        try:
            conn = get_db_connection()
            try:
                name, tag = req.riot_id.rsplit("#", 1)
                puuid = resolve_puuid(conn, name.strip(), tag.strip())
                if puuid:
                    summary = get_player_summary(conn, puuid)
                    telemetry = get_telemetry(conn, puuid)
                    matchup = get_matchup_diagnostics(conn, puuid)
                    aim_dist = get_aim_by_distance(conn, puuid)
                    aim_prof = _build_aim_profile(summary, telemetry, aim_dist)
                    profile = _profile_for_prompt(summary, aim_prof, telemetry, matchup)
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 — proceed without player context
            profile = {}

    # Retrieve grounding knowledge for the question.
    try:
        chunks = _get_retriever().retrieve(req.question)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Knowledge retrieval unavailable: {e}")

    messages = build_coaching_prompt(
        profile,
        [{"content": c.content, "source": c.source, "metadata": c.metadata} for c in chunks],
        req.question,
    )

    try:
        answer = llm.generate_coaching_response(messages)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

    return CoachingResponse(
        answer=answer,
        sources_used=[
            {"source": c.source, "score": round(c.score, 3), **c.metadata} for c in chunks
        ],
        player_stats_referenced=profile,
        follow_up_suggestions=[],
    )


@app.get("/api/v1/player/{riot_id}/heatmap")
async def get_death_heatmap(riot_id: str, map_id: str, last_n: int = 50, user: dict = Depends(get_current_user)):
    """Death/kill coordinates for a player on a map, normalized to 0–100% of the
    minimap so the frontend can position them directly with CSS."""
    name, tag = _split_riot_id(riot_id)
    conn = _connect()
    try:
        puuid = resolve_puuid(conn, name, tag)
        if not puuid:
            raise HTTPException(status_code=404, detail=f"No ingested data for {riot_id}.")
        locs = get_engagement_locations(conn, puuid, map_id, limit=last_n)
        # Prefer Riot's official minimap transform (aligns dots to the real map
        # image). Fall back to data-derived bounds for maps without official
        # calibration (e.g. TDM/HURM maps).
        if coordinates.has_official_calibration(map_id):
            samples = []
        else:
            samples = get_map_coord_samples(conn, map_id)
    finally:
        conn.close()

    minimap = coordinates.minimap_url(map_id)
    if minimap is not None:
        convert = lambda x, y: coordinates.official_to_percent(map_id, x, y)  # noqa: E731
        calibrated = True
    else:
        MIN_SAMPLES = 80
        if len(samples) >= MIN_SAMPLES:
            bounds = coordinates.derive_bounds(samples)
            calibrated = True
        else:
            bounds = coordinates.get_bounds(map_id)
            calibrated = coordinates.is_calibrated(map_id)
        convert = lambda x, y: coordinates.to_percent_with(bounds, x, y)  # noqa: E731

    def norm(points):
        return [{"x": px, "y": py} for x, y in points for px, py in [convert(x, y)]]

    return {
        "map_id": map_id,
        "calibrated": calibrated,
        "minimap_url": minimap,
        "deaths": norm(locs["deaths"]),
        "kills": norm(locs["kills"]),
    }


@app.post("/api/v1/feedback")
async def submit_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Record a thumbs up/down on a coaching answer (knowledge-gap signal)."""
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 or -1.")
    conn = _connect()
    try:
        puuid = None
        if req.riot_id and "#" in req.riot_id:
            name, tag = req.riot_id.rsplit("#", 1)
            puuid = resolve_puuid(conn, name.strip(), tag.strip())
        record_feedback(conn, puuid, req.question, req.rating, req.answer_excerpt, req.sources)
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/v1/player/{riot_id}/tilt")
async def get_tilt(riot_id: str, last_n: int = 100, user: dict = Depends(get_current_user)):
    """Session-level tilt analysis: segment matches into sessions and score each."""
    name, tag = _split_riot_id(riot_id)
    conn = _connect()
    try:
        puuid = resolve_puuid(conn, name, tag)
        if not puuid:
            raise HTTPException(status_code=404, detail=f"No ingested data for {riot_id}.")
        timeline = get_match_timeline(conn, puuid, limit=last_n)
    finally:
        conn.close()

    timestamps = [t for t, _ in timeline]
    acs_values = [a for _, a in timeline]
    sessions = detect_tilt(timestamps, acs_values)
    return {
        "match_count": len(timeline),
        "sessions": [asdict(s) for s in sessions],
    }


@app.get("/api/v1/player/{riot_id}/economy-impact")
async def get_economy_impact(riot_id: str, last_n: int = 20, user: dict = Depends(get_current_user)):
    """ACS broken down by economy round type (eco/force/full)."""
    name, tag = _split_riot_id(riot_id)
    conn = _connect()
    try:
        puuid = resolve_puuid(conn, name, tag)
        if not puuid:
            raise HTTPException(status_code=404, detail=f"No ingested data for {riot_id}.")
        split = get_economy_split(conn, puuid)
        return split
    finally:
        conn.close()

