"""
HUNTER.OS - Redis Connection Manager
Lazy connection pool for rate limiting, caching, and event bus.
Falls back gracefully when Redis is unavailable.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False


def get_redis():
    """Return a Redis client if REDIS_URL is configured and reachable, else None."""
    global _redis_client, _redis_checked

    if _redis_checked:
        return _redis_client

    _redis_checked = True

    from app.core.config import settings

    if not settings.REDIS_URL:
        logger.info("REDIS_URL not set — using in-memory fallbacks")
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        _redis_client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — using in-memory fallbacks", exc)
        _redis_client = None

    return _redis_client


def reset_redis():
    """Reset cached client (for testing)."""
    global _redis_client, _redis_checked
    _redis_client = None
    _redis_checked = False
