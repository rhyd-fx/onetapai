import os
import sys

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    RANKED_MODES,
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
import redis
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

# Initialize Redis client.
try:
    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Failed to connect to Redis: {e}")
    redis_client = None

_memory_cache: Dict[str, Dict[str, Any]] = {}

def get_cache_value(key: str) -> str | None:
    if redis_client:
        try:
            return redis_client.get(key)
        except Exception:
            pass
    return json.dumps(_memory_cache.get(key)) if key in _memory_cache else None

def set_cache_value(key: str, value: str, ttl: int) -> None:
    if redis_client:
        try:
            redis_client.setex(key, ttl, value)
            return
        except Exception:
            pass
    _memory_cache[key] = json.loads(value)

def delete_cache_value(key: str) -> None:
    if redis_client:
        try:
            redis_client.delete(key)
            return
        except Exception:
            pass
    _memory_cache.pop(key, None)

def _send_verification_email(email: str, code: str) -> None:
    subject = "Verify your OneTap AI account"
    body = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0c0f12; color: #f0f4f8; padding: 30px; border-radius: 8px; max-width: 600px; margin: 0 auto; border: 1px solid #1a222a;">
        <h2 style="color: #ff4655; border-bottom: 2px solid #ff4655; padding-bottom: 10px; margin-top: 0;">Welcome to OneTap AI!</h2>
        <p style="font-size: 16px; line-height: 1.5; color: #a0aab5;">Please use the following 6-digit verification code to activate your account:</p>
        <div style="background-color: #161c22; border: 1px solid #ff4655; border-radius: 6px; padding: 15px; text-align: center; margin: 25px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #ff4655;">{code}</span>
        </div>
        <p style="font-size: 14px; color: #6d7a86; line-height: 1.5;">This code will expire in 15 minutes. If you did not request this, you can safely ignore this email.</p>
        <hr style="border: 0; border-top: 1px solid #1c2630; margin: 30px 0;" />
        <p style="font-size: 11px; text-align: center; color: #52606d;">OneTap AI Coaching Platform &copy; 2026</p>
    </div>
    """
    
    # Always print clearly to the console logs
    print(f"\n==================================================")
    print(f"[EMAIL VERIFICATION] To: {email} | Code: {code}")
    print(f"==================================================\n")
    
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    if not (smtp_host and smtp_port and smtp_user and smtp_password):
        return
        
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=5)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=5)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, email, msg.as_string())
        server.quit()
        print(f"Verification email successfully sent to {email}")
    except Exception as e:
        print(f"Error sending verification email to {email}: {e}")

DISPOSABLE_DOMAINS = set([
    "10minutemail.com", "10minutemail.co.uk", "tempmail.com", "temp-mail.org",
    "mailinator.com", "yopmail.com", "guerrillamail.com", "guerrillamailblock.com",
    "guerrillamail.net", "guerrillamail.org", "guerrillamail.biz", "sharklasers.com",
    "dispostable.com", "getairmail.com", "throwawaymail.com", "generator.email",
    "maildrop.cc", "mailnesia.com", "mailac.co", "mintemail.com", "mytrashmail.com",
    "getnada.com", "boun.cr", "trashmail.com", "burnermail.io", "tempmailaddress.com",
    "fakeinbox.com", "moakt.com", "emailondeck.com", "harakirimail.com",
    "mailcatch.com", "fastmail.xyz", "temp-mail.ru", "temp-mail.com", "disposable.com",
    "zillamail.com", "spambox.us", "discardmail.com", "mailnull.com"
])

def _fetch_disposable_domains_task():
    global DISPOSABLE_DOMAINS
    import urllib.request
    import time
    
    cache_path = os.path.join(os.path.dirname(__file__), "disposable_domains_cache.json")
    
    # 1. Load from local cache file first
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                cached_list = json.load(f)
                DISPOSABLE_DOMAINS = set(cached_list)
                print(f"Loaded {len(DISPOSABLE_DOMAINS)} disposable domains from local cache file.")
    except Exception as e:
        print(f"Error loading local disposable domains cache file: {e}")

    # 2. Fetch from GitHub and save to cache file, repeating every 24 hours
    url = "https://raw.githubusercontent.com/kickbox/disposable-email-domains/master/list.json"
    while True:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                domains = json.loads(response.read().decode())
                if isinstance(domains, list) and len(domains) > 0:
                    DISPOSABLE_DOMAINS = set(domains)
                    with open(cache_path, "w") as f:
                        json.dump(domains, f)
                    print(f"Successfully refreshed disposable domains list from Kickbox GitHub ({len(domains)} domains).")
        except Exception as e:
            print(f"Failed to fetch disposable domains from GitHub: {e}. Will retry in next interval.")
        
        # Sleep for 24 hours
        time.sleep(86400)

def _is_disposable_email(email: str) -> bool:
    if "@" not in email:
        return False
    _, domain = email.rsplit("@", 1)
    domain = domain.lower().strip()
    
    global DISPOSABLE_DOMAINS
    if domain in DISPOSABLE_DOMAINS:
        return True
        
    parts = domain.split(".")
    # Check parent domains (subdomains)
    for i in range(1, len(parts) - 1):
        parent_domain = ".".join(parts[i:])
        if parent_domain in DISPOSABLE_DOMAINS:
            return True
            
    return False

@app.on_event("startup")
async def startup_event():
    import threading
    t = threading.Thread(target=_fetch_disposable_domains_task, daemon=True)
    t.start()

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

# Rate limiting (per client IP). Throttles credential brute-force on the auth
# endpoints and abuse of the external-API-fanning analyze/coach endpoints.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Per-account login lockout. The IP rate limit above is bypassable with rotating
# IPs; this caps failed attempts against a single account regardless of source.
# In-process (single-worker) — move to Redis for multi-worker deployments.
import threading
import time as _time

_LOGIN_MAX_FAILS = 5
_LOGIN_LOCKOUT_SECONDS = 900  # 15 min
_login_fails: dict[str, tuple[int, float]] = {}  # key -> (count, first_fail_ts)
_login_fails_lock = threading.Lock()


def _login_locked(key: str) -> bool:
    with _login_fails_lock:
        entry = _login_fails.get(key)
        if not entry:
            return False
        count, first_ts = entry
        if _time.time() - first_ts > _LOGIN_LOCKOUT_SECONDS:
            del _login_fails[key]  # window expired
            return False
        return count >= _LOGIN_MAX_FAILS


def _record_login_fail(key: str) -> None:
    with _login_fails_lock:
        count, first_ts = _login_fails.get(key, (0, _time.time()))
        if _time.time() - first_ts > _LOGIN_LOCKOUT_SECONDS:
            count, first_ts = 0, _time.time()  # reset stale window
        _login_fails[key] = (count + 1, first_ts)


def _clear_login_fails(key: str) -> None:
    with _login_fails_lock:
        _login_fails.pop(key, None)

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
    # Game-mode filter. Omitted/None -> Ranked (Competitive + Premier);
    # [] -> all modes; ["Unrated", ...] -> those modes only.
    game_modes: list[str] | None = None
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


class VerifyRegisterRequest(BaseModel):
    email: str
    code: str


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
        # Log the real error server-side; return a generic message so DSN/host
        # fragments aren't leaked to clients.
        print(f"DB connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable. Please try again shortly.")


def _build_aim_profile(summary: dict, telemetry: dict | None = None, aim_by_distance: list[dict] | None = None) -> dict:
    """Run the mechanical AimProfile classifier on aggregate hit stats using telemetry and range stats."""
    hs = summary.get("headshot_pct")
    bs = summary.get("bodyshot_pct")
    ls = summary.get("legshot_pct")
    if hs is None or bs is None:
        return {"available": False, "reason": "no hit-distribution data yet"}

    # Fall back to the overall HS rate for range buckets with no kills — an
    # empty bucket is missing data, not a 0% headshot rate (which would falsely
    # trigger OVER_FLICKING).
    hs_short = hs
    hs_long = hs
    if aim_by_distance:
        close_stats = next((a for a in aim_by_distance if a["range"] == "close"), None)
        long_stats = next((a for a in aim_by_distance if a["range"] == "long"), None)
        if close_stats and close_stats.get("kills"):
            hs_short = (close_stats.get("headshot_pct") or 0.0) / 100
        if long_stats and long_stats.get("kills"):
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
@limiter.limit("5/minute")
async def auth_register(request: Request, req: RegisterRequest):
    username = req.username.strip()
    email = req.email.strip().lower()
    password = req.password
    
    if _is_disposable_email(email):
        raise HTTPException(
            status_code=400,
            detail="Disposable or temporary email addresses are not allowed. Please use a valid, permanent email address."
        )
        
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters.")
        
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username or email is already registered.")
    finally:
        conn.close()
        
    pwd_hash = hash_password(password)
    
    # Generate 6-digit numeric verification code
    code = f"{random.randint(100000, 999999)}"
    
    # Store registration details in cache for 15 minutes
    reg_data = {
        "username": username,
        "email": email,
        "password_hash": pwd_hash,
        "code": code
    }
    
    set_cache_value(f"verify_reg:{email}", json.dumps(reg_data), 900)
    
    # Send verification email asynchronously / best-effort
    _send_verification_email(email, code)
    
    return {
        "status": "verification_sent",
        "email": email,
        "message": "Verification code sent to your email address."
    }


@app.post("/api/v1/auth/verify")
@limiter.limit("10/minute")
async def auth_verify(request: Request, req: VerifyRegisterRequest):
    email = req.email.strip().lower()
    code = req.code.strip()
    
    cached_data_str = get_cache_value(f"verify_reg:{email}")
    if not cached_data_str:
        raise HTTPException(status_code=400, detail="Verification code expired or not found. Please sign up again.")
        
    reg_data = json.loads(cached_data_str)
    if reg_data.get("code") != code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
        
    username = reg_data["username"]
    pwd_hash = reg_data["password_hash"]
    
    conn = _connect()
    try:
        with conn.cursor() as cur:
            # Recheck just in case someone registered in the meantime
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username or email is already registered.")
                
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, pwd_hash)
            )
            conn.commit()
            
            # Get user ID
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
    finally:
        conn.close()
        
    # Delete from cache
    delete_cache_value(f"verify_reg:{email}")
    
    # Generate JWT token directly so they are immediately logged in
    token = generate_jwt({
        "user_id": user["id"],
        "username": username,
        "email": email
    })
    
    return {
        "token": token,
        "username": username
    }


@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")
async def auth_login(request: Request, req: LoginRequest):
    user_input = req.username_or_email.strip()
    password = req.password

    lockout_key = user_input.lower()
    if _login_locked(lockout_key):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in 15 minutes.",
        )

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = %s OR email = %s",
                (user_input, user_input)
            )
            user = cur.fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                _record_login_fail(lockout_key)
                raise HTTPException(status_code=401, detail="Invalid username or password.")

            _clear_login_fails(lockout_key)
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
@limiter.limit("20/minute")
async def analyze_player(request: Request, req: AnalysisRequest, user: dict = Depends(get_current_user)):
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

        # None (omitted) -> Ranked default; [] -> all modes; [..] -> those modes.
        modes = list(RANKED_MODES) if req.game_modes is None else req.game_modes
        summary = get_player_summary(conn, puuid, req.season_id, game_modes=modes)
        trajectory = get_acs_trajectory(conn, puuid, limit=req.match_count, season_id=req.season_id, game_modes=modes)
        telemetry = get_telemetry(conn, puuid, req.season_id, game_modes=modes)
        top_maps = get_top_maps(conn, puuid, req.season_id, game_modes=modes)
        top_weapons = get_top_weapons(conn, puuid, req.season_id, game_modes=modes)
        aim_by_distance = get_aim_by_distance(conn, puuid, req.season_id, game_modes=modes)
        economy_efficiency = get_economy_efficiency(conn, puuid, req.season_id, game_modes=modes)
        side_bias = get_side_bias(conn, puuid, req.season_id, game_modes=modes)
        hardware_check = get_hardware_check(conn, puuid)
        seasons = get_player_seasons(conn, puuid)
        matchup_diagnostics = get_matchup_diagnostics(conn, puuid, req.season_id, game_modes=modes)
        economy_split = get_economy_split(conn, puuid, req.season_id, game_modes=modes)
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
@limiter.limit("15/minute")
async def coaching_chat(request: Request, req: CoachingQuestion, user: dict = Depends(get_current_user)):
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
        print(f"Knowledge retrieval failed: {e}")
        raise HTTPException(status_code=503, detail="Coaching knowledge is temporarily unavailable.")

    messages = build_coaching_prompt(
        profile,
        [{"content": c.content, "source": c.source, "metadata": c.metadata} for c in chunks],
        req.question,
    )

    try:
        answer = llm.generate_coaching_response(messages)
    except Exception as e:  # noqa: BLE001
        print(f"LLM generation failed: {e}")
        raise HTTPException(status_code=502, detail="The coach is temporarily unavailable. Please try again.")

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

