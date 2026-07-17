"""Central configuration for the OneTap AI backend.

All secrets and environment-specific settings are read from environment
variables, optionally seeded from a `.env` file at the repository root.

NEVER hardcode credentials in source. Copy `.env.example` to `.env` and fill
it in for local development. Real environment variables always take precedence
over values in the `.env` file.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repository root = parent of the `backend/` directory that holds this file.
REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Minimal, dependency-free `.env` loader.

    Parses simple `KEY=VALUE` lines (ignoring blanks and `#` comments) and
    seeds them into the process environment *without* overriding variables
    that are already set in the real environment.
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()


def get(name: str, default: str | None = None) -> str | None:
    """Return an environment variable, or `default` if unset/empty."""
    val = os.environ.get(name)
    return val if val else default


def require(name: str) -> str:
    """Return a required environment variable, or raise a clear error.

    Use for secrets that have no safe default (external API keys).
    """
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            f"Copy .env.example to .env and fill it in (see README)."
        )
    return val


# --- Database (MariaDB) ---
# Dev defaults mirror docker-compose.yml so local runs work with zero config.
# Override via environment / .env in any real deployment.
DB_HOST = get("DB_HOST", "localhost")
DB_PORT = int(get("DB_PORT", "3306"))
DB_USER = get("DB_USER", "onetapai_user")
DB_PASSWORD = get("DB_PASSWORD", "onetapai_password")
DB_NAME = get("DB_NAME", "onetapai")

# --- Data source API (no safe default — require at call site) ---
HENRIK_API_KEY = get("HENRIK_API_KEY")
RIOT_API_KEY = get("RIOT_API_KEY")

# --- Embeddings (FastEmbed — local, no API key, runs on CPU) ---
# Model name and its output dimension MUST stay in sync. If you change the
# model, update EMBEDDING_DIM to match and recreate the Qdrant collection.
#   BAAI/bge-small-en-v1.5 -> 384   |   BAAI/bge-base-en-v1.5 -> 768
EMBEDDING_MODEL = get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = int(get("EMBEDDING_DIM", "384"))
# Sparse (lexical BM25) model for hybrid retrieval — local, tiny, no weights.
SPARSE_EMBEDDING_MODEL = get("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25")

# --- LLM generation (OpenRouter — OpenAI-compatible API) ---
# Pick any model from https://openrouter.ai/models (append ":free" for free tier).
OPENROUTER_API_KEY = get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# --- Vector DB (Qdrant) ---
QDRANT_HOST = get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(get("QDRANT_PORT", "6333"))
# Optional. If set, must match Qdrant's QDRANT__SERVICE__API_KEY. Leave unset
# for local dev; set in any deployment where Qdrant is network-reachable.
QDRANT_API_KEY = get("QDRANT_API_KEY")
QDRANT_HTTPS = get("QDRANT_HTTPS", "false").lower() == "true"


# --- Cache / queue (Redis) ---
REDIS_URL = get("REDIS_URL", "redis://localhost:6379/0")
# Optional. Used when REDIS_URL doesn't embed the password (redis://:pass@host).
# Must match the requirepass the redis container was started with.
REDIS_PASSWORD = get("REDIS_PASSWORD") or None

# --- API server ---
CORS_ORIGINS = [
    o.strip()
    for o in (get("CORS_ORIGINS", "http://localhost:3000") or "").split(",")
    if o.strip()
]
# Also allow localhost + private-LAN origins on any port (so the frontend works
# when accessed via a machine's LAN IP in dev, not just localhost). Scoped to
# localhost/LAN by default — NOT a wildcard, which would defeat CORS entirely
# when combined with allow_credentials. Override via CORS_ORIGIN_REGEX for prod.
CORS_ORIGIN_REGEX = get(
    "CORS_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1|(10|172\.(1[6-9]|2\d|3[01])|192\.168)\.[\d.]+)(:\d+)?",
)

# --- Henrik API rate limiting (free tier is ~30 req/min) ---
HENRIK_RPM = int(get("HENRIK_RPM", "25"))                 # requests/minute (leave margin under 30)
HENRIK_MAX_CONCURRENCY = int(get("HENRIK_MAX_CONCURRENCY", "4"))

# --- Ingestion backfill ---
BACKFILL_TARGET = int(get("BACKFILL_TARGET", "1000"))     # new matches to ingest per run
BACKFILL_SIZE = int(get("BACKFILL_SIZE", "10"))           # matches requested per player

# --- Raw JSON archival (S3 / MinIO) ---
# Leave S3_ENDPOINT_URL unset to archive to local disk only. Set it (e.g.
# http://localhost:9000) to also push each raw match to an S3/MinIO bucket.
S3_ENDPOINT_URL = get("S3_ENDPOINT_URL")
S3_BUCKET = get("S3_BUCKET", "onetapai-raw")
S3_ACCESS_KEY = get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = get("S3_SECRET_KEY", "minioadmin")
S3_REGION = get("S3_REGION", "us-east-1")
