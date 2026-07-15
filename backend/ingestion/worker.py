"""Async Henrik Dev API client with a real token-bucket rate limiter.

The previous implementation used an asyncio.Semaphore as a "rate limiter",
which only bounds *concurrency* — throughput could still blow past the free
tier. This version bounds the actual request RATE (tokens/second) with a token
bucket, and keeps a separate small concurrency cap.
"""
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from urllib.parse import quote

import aiohttp

# Henrik/Riot valid platform regions. Guards against path injection via a
# user-supplied region and against wasted calls to nonexistent endpoints.
VALID_REGIONS = frozenset({"na", "eu", "ap", "kr", "latam", "br"})

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config


@dataclass(frozen=True)
class RateLimitConfig:
    """Henrik Dev API rate limits. Free tier is ~30 req/min."""
    requests_per_minute: int = 25    # tokens refilled per minute (margin under 30)
    burst: int = 5                   # bucket capacity (max tokens available at once)
    max_concurrency: int = 4         # simultaneous in-flight requests
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_max_attempts: int = 5


class AsyncTokenBucket:
    """Async token bucket. `acquire()` blocks until a token is available,
    bounding the true request rate regardless of how many coroutines call it."""

    def __init__(self, rate_per_sec: float, capacity: float):
        self._rate = rate_per_sec
        self._capacity = capacity
        self._tokens = capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                # Refill based on elapsed time.
                self._tokens = min(
                    self._capacity, self._tokens + (now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)


class HenrikAPIClient:
    def __init__(self, api_key: str, rate_config: RateLimitConfig | None = None):
        self._api_key = api_key
        self._base_url = "https://api.henrikdev.xyz"
        self._config = rate_config or RateLimitConfig()
        self._bucket = AsyncTokenBucket(
            self._config.requests_per_minute / 60.0, self._config.burst
        )
        self._semaphore = asyncio.Semaphore(self._config.max_concurrency)
        self._session: aiohttp.ClientSession | None = None

    @classmethod
    def from_config(cls) -> "HenrikAPIClient":
        """Build a client from the shared config / .env (requires HENRIK_API_KEY)."""
        return cls(
            config.require("HENRIK_API_KEY"),
            RateLimitConfig(
                requests_per_minute=config.HENRIK_RPM,
                max_concurrency=config.HENRIK_MAX_CONCURRENCY,
            ),
        )

    async def _request(self, url: str) -> dict:
        """Rate-limited request with exponential backoff on 429s."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": self._api_key}
            )

        for attempt in range(self._config.retry_max_attempts):
            await self._bucket.acquire()  # rate limit (true tokens/sec)
            retry_after = self._config.retry_base_delay
            async with self._semaphore:  # concurrency limit
                async with self._session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    if resp.status == 429:
                        retry_after = float(
                            resp.headers.get("Retry-After", self._config.retry_base_delay)
                        )
                    else:
                        resp.raise_for_status()
            # Back off OUTSIDE the semaphore so we don't hold a slot while sleeping.
            delay = min(retry_after * (2 ** attempt), self._config.retry_max_delay)
            await asyncio.sleep(delay)

        raise RuntimeError(f"Exhausted retries for {url}")

    async def get_account(self, name: str, tag: str) -> dict:
        """Fetch account info to get PUUID and region."""
        url = (
            f"{self._base_url}/valorant/v1/account/"
            f"{quote(name, safe='')}/{quote(tag, safe='')}"
        )
        data = await self._request(url)
        return data["data"]

    async def get_matches(
        self, region: str, name: str, tag: str, size: int = 5
    ) -> list[dict]:
        """Fetch latest full matches for a player (Henrik v3)."""
        region = region.lower().strip()
        if region not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region {region!r}; expected one of {sorted(VALID_REGIONS)}."
            )
        size = max(1, min(int(size), 10))  # clamp to Henrik's supported range
        url = (
            f"{self._base_url}/valorant/v3/matches/"
            f"{region}/{quote(name, safe='')}/{quote(tag, safe='')}"
            f"?size={size}&filter=competitive"
        )
        data = await self._request(url)
        return data.get("data", [])

    async def close(self):
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
