"""
HUNTER.OS - Rate Limiter & Login Attempt Tracker

Supports Redis-backed (production) and in-memory (development) modes.
Automatically selects backend based on REDIS_URL configuration.
"""
import time
import threading
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# ── In-Memory Implementation ──────────────────────────────────────

class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter (single-process only)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300

    def check(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._maybe_cleanup(now)
            if key not in self._requests:
                self._requests[key] = [now]
                return True
            cutoff = now - self.window_seconds
            self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]
            if len(self._requests[key]) >= self.max_requests:
                logger.warning("Rate limit exceeded", extra={"key": key, "limit": self.max_requests})
                return False
            self._requests[key].append(now)
            return True

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        cutoff = now - self.window_seconds
        stale_keys = [
            k for k, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for k in stale_keys:
            del self._requests[k]
        self._last_cleanup = now

    def reset(self, key: str) -> None:
        with self._lock:
            self._requests.pop(key, None)


class InMemoryLoginTracker:
    """Track consecutive failed logins per email (single-process only)."""

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts: Dict[str, Tuple[int, float | None]] = {}
        self._lock = threading.Lock()

    def is_locked(self, email: str) -> bool:
        with self._lock:
            entry = self._attempts.get(email)
            if entry is None:
                return False
            failures, locked_at = entry
            if locked_at is None:
                return False
            if time.monotonic() - locked_at >= self.lockout_seconds:
                del self._attempts[email]
                return False
            return True

    def record_failure(self, email: str) -> None:
        with self._lock:
            entry = self._attempts.get(email)
            failures = 1 if entry is None else entry[0] + 1
            locked_at = None
            if failures >= self.max_attempts:
                locked_at = time.monotonic()
                logger.warning(
                    "Account locked due to repeated failed logins",
                    extra={"email": email, "attempts": failures},
                )
            self._attempts[email] = (failures, locked_at)

    def record_success(self, email: str) -> None:
        with self._lock:
            self._attempts.pop(email, None)

    def reset(self, email: str) -> None:
        with self._lock:
            self._attempts.pop(email, None)


# ── Redis Implementation ──────────────────────────────────────────

class RedisRateLimiter:
    """Sliding window rate limiter using Redis sorted sets. Multi-process safe."""

    def __init__(self, redis_client, max_requests: int, window_seconds: int, prefix: str = "rl") -> None:
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def check(self, key: str) -> bool:
        redis_key = f"{self.prefix}:{key}"
        now = time.time()
        cutoff = now - self.window_seconds

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {f"{now}": now})
        pipe.expire(redis_key, self.window_seconds + 1)
        results = pipe.execute()

        count = results[1]
        if count >= self.max_requests:
            logger.warning("Rate limit exceeded (Redis)", extra={"key": key, "limit": self.max_requests})
            # Remove the just-added entry
            self.redis.zrem(redis_key, f"{now}")
            return False
        return True

    def reset(self, key: str) -> None:
        self.redis.delete(f"{self.prefix}:{key}")


class RedisLoginTracker:
    """Track failed login attempts using Redis hashes with TTL."""

    def __init__(self, redis_client, max_attempts: int = 5, lockout_seconds: int = 900, prefix: str = "login") -> None:
        self.redis = redis_client
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.prefix = prefix

    def is_locked(self, email: str) -> bool:
        locked_key = f"{self.prefix}:locked:{email}"
        return self.redis.exists(locked_key) == 1

    def record_failure(self, email: str) -> None:
        fail_key = f"{self.prefix}:fails:{email}"
        locked_key = f"{self.prefix}:locked:{email}"

        failures = self.redis.incr(fail_key)
        self.redis.expire(fail_key, self.lockout_seconds)

        if failures >= self.max_attempts:
            self.redis.set(locked_key, "1", ex=self.lockout_seconds)
            logger.warning(
                "Account locked due to repeated failed logins (Redis)",
                extra={"email": email, "attempts": failures},
            )

    def record_success(self, email: str) -> None:
        self.redis.delete(f"{self.prefix}:fails:{email}")
        self.redis.delete(f"{self.prefix}:locked:{email}")

    def reset(self, email: str) -> None:
        self.redis.delete(f"{self.prefix}:fails:{email}")
        self.redis.delete(f"{self.prefix}:locked:{email}")


# ── Factory: Auto-select backend ──────────────────────────────────

def _create_rate_limiter(max_requests: int, window_seconds: int, prefix: str = "rl"):
    """Create rate limiter with Redis if available, else in-memory."""
    from app.core.redis import get_redis
    redis_client = get_redis()
    if redis_client:
        return RedisRateLimiter(redis_client, max_requests, window_seconds, prefix)
    return InMemoryRateLimiter(max_requests, window_seconds)


def _create_login_tracker(max_attempts: int = 5, lockout_seconds: int = 900):
    """Create login tracker with Redis if available, else in-memory."""
    from app.core.redis import get_redis
    redis_client = get_redis()
    if redis_client:
        return RedisLoginTracker(redis_client, max_attempts, lockout_seconds)
    return InMemoryLoginTracker(max_attempts, lockout_seconds)


# ── Lazy singletons (initialized on first use) ───────────────────

_login_limiter = None
_register_limiter = None
_login_tracker = None


def get_login_rate_limiter():
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = _create_rate_limiter(max_requests=5, window_seconds=60, prefix="rl:login")
    return _login_limiter


def get_register_rate_limiter():
    global _register_limiter
    if _register_limiter is None:
        _register_limiter = _create_rate_limiter(max_requests=3, window_seconds=60, prefix="rl:register")
    return _register_limiter


def get_login_attempt_tracker():
    global _login_tracker
    if _login_tracker is None:
        _login_tracker = _create_login_tracker(max_attempts=5, lockout_seconds=900)
    return _login_tracker


# ── Backward-compatible singletons (lazy proxy) ──────────────────
# Old code uses: login_rate_limiter.check(key)
# These proxies forward to the lazy factory functions above.

class _LazyProxy:
    def __init__(self, factory):
        self._factory = factory
        self._instance = None

    def _get(self):
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def check(self, key: str) -> bool:
        return self._get().check(key)

    def is_locked(self, email: str) -> bool:
        return self._get().is_locked(email)

    def record_failure(self, email: str) -> None:
        return self._get().record_failure(email)

    def record_success(self, email: str) -> None:
        return self._get().record_success(email)

    def reset(self, key: str) -> None:
        return self._get().reset(key)


login_rate_limiter = _LazyProxy(get_login_rate_limiter)
register_rate_limiter = _LazyProxy(get_register_rate_limiter)
login_attempt_tracker = _LazyProxy(get_login_attempt_tracker)
