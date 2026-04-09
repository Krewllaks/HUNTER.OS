"""
HUNTER.OS - Cache Layer (Phase 11)
================================================
Thin async wrapper around the existing sync Redis client (app.core.redis).

Why this exists
---------------
Phase 11 cost-optimization needs aggressive caching of:
  * SERP query results (ScrapingDog / stealth Google)
  * Footprint scan results (per username / per lead)
  * Email / profile enrichment results (per domain / per email)
  * TR source agent results (TOBB, KOSGEB, Chamber, etc.)

Reusing the same lead / domain across products must NEVER trigger a
second paid API call within CACHE_TTL_DAYS (default 30 days). This module
is the single choke point that enforces that guarantee.

Design notes
------------
* Built on top of ``app.core.redis.get_redis`` (sync client) — we do NOT
  open a second connection pool. We wrap blocking ops with
  ``asyncio.to_thread`` so callers stay fully async.
* Graceful degradation: if Redis is unreachable (dev laptops, CI,
  Railway cold start) every helper returns a miss / no-op instead of
  raising, so the rest of the pipeline keeps running.
* Deterministic keys (sha1 of lowercased joined parts) make the cache
  safe to share across processes, workers, and dynos.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Namespacing: every key we put into Redis is prefixed "hunter:"
# so a flush by pattern is safe (never touches non-hunter keys).
_KEY_PREFIX: str = "hunter"


def _default_ttl_seconds() -> int:
    """Return the default TTL in seconds (``CACHE_TTL_DAYS`` * 86400)."""
    return max(1, int(settings.CACHE_TTL_DAYS) * 86400)


def cache_key(namespace: str, *parts: Any) -> str:
    """
    Build a deterministic cache key of the form ``hunter:{namespace}:{hash}``.

    Parameters
    ----------
    namespace : str
        Logical bucket name, e.g. ``"serp"``, ``"footprint"``, ``"apollo"``.
    *parts : Any
        Arbitrary identifiers (strings, numbers, None). They are lowercased,
        stripped, joined with ``|`` and hashed with SHA-1. ``None`` and
        empty parts are ignored so callers can pass optional fields safely.

    Returns
    -------
    str
        A stable key like ``hunter:serp:3f9a7b2c1d4e5f60``.

    Examples
    --------
    >>> cache_key("serp", "site:linkedin.com 'CTO' 'Istanbul'")
    'hunter:serp:...'
    >>> cache_key("email", "Ahmet", "Yılmaz", "acme.com.tr")
    'hunter:email:...'
    """
    cleaned: list[str] = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip().lower()
        if text:
            cleaned.append(text)
    joined = "|".join(cleaned) if cleaned else "∅"
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]
    return f"{_KEY_PREFIX}:{namespace}:{digest}"


async def cache_get(key: str) -> Optional[dict]:
    """
    Fetch a JSON-serialisable dict from Redis.

    Returns ``None`` when:
      * Redis is not configured / unreachable
      * the key does not exist
      * the stored payload is not valid JSON (treated as a miss)

    This function NEVER raises — callers can rely on a plain ``None`` miss.
    """
    client = get_redis()
    if client is None:
        return None

    try:
        raw = await asyncio.to_thread(client.get, key)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("cache_get(%s) failed, treating as miss: %s", key, exc)
        return None

    if raw is None:
        return None

    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        logger.warning("cache_get(%s) corrupted JSON, dropping: %s", key, exc)
        return None

    return value if isinstance(value, dict) else None


async def cache_set(
    key: str,
    value: dict,
    ttl: Optional[int] = None,
) -> bool:
    """
    Store a JSON-serialisable dict in Redis with a TTL.

    Parameters
    ----------
    key : str
        Use :func:`cache_key` to build this.
    value : dict
        Any JSON-serialisable dict. Non-JSON types are coerced to ``str``
        via ``default=str`` so datetimes etc. don't explode.
    ttl : int, optional
        Lifetime in seconds. Defaults to ``CACHE_TTL_DAYS * 86400``
        (30 days). Minimum 1 second.

    Returns
    -------
    bool
        ``True`` if the write succeeded, ``False`` if Redis was
        unavailable or the payload could not be serialised. Never raises.
    """
    client = get_redis()
    if client is None:
        return False

    if not isinstance(value, dict):
        logger.debug("cache_set(%s) skipped, value is not a dict", key)
        return False

    try:
        payload = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        logger.warning("cache_set(%s) could not serialise value: %s", key, exc)
        return False

    expire = ttl if (ttl is not None and ttl > 0) else _default_ttl_seconds()

    try:
        await asyncio.to_thread(client.setex, key, expire, payload)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("cache_set(%s) failed silently: %s", key, exc)
        return False


# Backwards-compatible alias: the Phase 11 plan mentioned ``cache_set_ttl``
# as a discoverable name. We export both so either spelling works.
cache_set_ttl = cache_set


async def is_cached(key: str) -> bool:
    """Return ``True`` if ``key`` currently exists in Redis."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await asyncio.to_thread(client.exists, key))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("is_cached(%s) failed, treating as miss: %s", key, exc)
        return False


async def invalidate_key(key: str) -> bool:
    """Delete a single cache entry. Returns ``True`` if something was removed."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await asyncio.to_thread(client.delete, key))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("invalidate_key(%s) failed: %s", key, exc)
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    Delete every key matching a glob pattern. Intended for admin ops
    (e.g. ``invalidate_pattern("hunter:serp:*")`` after a provider change).

    Uses SCAN + DEL batches to avoid blocking Redis on large keyspaces.
    Returns the number of keys removed. On error returns ``0``.
    """
    client = get_redis()
    if client is None:
        return 0

    # Safety rail: never allow a bare "*" — that would flush non-hunter keys.
    if not pattern or pattern == "*":
        logger.warning("invalidate_pattern refused unsafe pattern: %r", pattern)
        return 0

    def _scan_and_delete() -> int:
        removed = 0
        cursor = 0
        while True:
            cursor, batch = client.scan(cursor=cursor, match=pattern, count=500)
            if batch:
                removed += client.delete(*batch)
            if cursor == 0:
                break
        return removed

    try:
        return await asyncio.to_thread(_scan_and_delete)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("invalidate_pattern(%s) failed: %s", pattern, exc)
        return 0


__all__ = [
    "cache_key",
    "cache_get",
    "cache_set",
    "cache_set_ttl",
    "is_cached",
    "invalidate_key",
    "invalidate_pattern",
]
