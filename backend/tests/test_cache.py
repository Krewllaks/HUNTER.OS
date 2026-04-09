"""
HUNTER.OS - Tests for app.core.cache
================================================
Unit tests for the Phase 11 cache layer.

Every test mocks ``app.core.redis.get_redis`` — no real Redis instance
is ever contacted. We assert both the happy path AND the degraded path
(Redis down / corrupted JSON) because graceful degradation is the whole
point of this module.

These tests use ``asyncio.run(...)`` instead of pytest-asyncio so the
suite stays dependency-free (pytest-asyncio is not in requirements.txt
and we don't want to add a test-only dep just for four files).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.core import cache as cache_module
from app.core.cache import (
    cache_get,
    cache_key,
    cache_set,
    cache_set_ttl,
    invalidate_key,
    invalidate_pattern,
    is_cached,
)


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def _run(coro):
    """Run an async coroutine synchronously inside a test."""
    return asyncio.run(coro)


def _fake_redis() -> MagicMock:
    """Build a MagicMock shaped like a sync redis.Redis client."""
    client = MagicMock(name="FakeRedis")
    client.get.return_value = None
    client.setex.return_value = True
    client.exists.return_value = 0
    client.delete.return_value = 0
    client.scan.return_value = (0, [])
    return client


# ─────────────────────────────────────────────────────
# cache_key — deterministic, safe to share across processes
# ─────────────────────────────────────────────────────
class TestCacheKey:
    def test_deterministic_same_inputs_produce_same_key(self):
        k1 = cache_key("serp", "site:linkedin.com 'CTO'")
        k2 = cache_key("serp", "site:linkedin.com 'CTO'")
        assert k1 == k2

    def test_different_namespaces_produce_different_keys(self):
        assert cache_key("serp", "acme") != cache_key("footprint", "acme")

    def test_case_and_whitespace_normalised(self):
        k1 = cache_key("email", "Ahmet", "Yılmaz", "Acme.Com.Tr")
        k2 = cache_key("email", "  ahmet ", "yılmaz", "acme.com.tr")
        assert k1 == k2

    def test_has_hunter_prefix_and_namespace(self):
        key = cache_key("serp", "foo")
        assert key.startswith("hunter:serp:")

    def test_ignores_none_and_empty_parts(self):
        k1 = cache_key("email", "ahmet", None, "", "acme.com")
        k2 = cache_key("email", "ahmet", "acme.com")
        assert k1 == k2

    def test_all_empty_parts_still_produce_stable_key(self):
        key = cache_key("serp", None, "", None)
        assert key.startswith("hunter:serp:")
        assert len(key.split(":")[-1]) == 16

    def test_key_hash_is_16_hex_chars(self):
        tail = cache_key("x", "y").split(":")[-1]
        assert len(tail) == 16
        int(tail, 16)  # must be valid hex


# ─────────────────────────────────────────────────────
# cache_get — returns dict on hit, None on miss / error
# ─────────────────────────────────────────────────────
class TestCacheGet:
    def test_hit_returns_parsed_dict(self):
        payload = {"results": [{"title": "t", "url": "u"}], "cached": True}
        fake = _fake_redis()
        fake.get.return_value = json.dumps(payload)

        with patch.object(cache_module, "get_redis", return_value=fake):
            got = _run(cache_get("hunter:serp:abc"))

        assert got == payload
        fake.get.assert_called_once_with("hunter:serp:abc")

    def test_miss_returns_none(self):
        fake = _fake_redis()
        fake.get.return_value = None
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_get("hunter:serp:xyz")) is None

    def test_redis_unavailable_returns_none(self):
        with patch.object(cache_module, "get_redis", return_value=None):
            assert _run(cache_get("hunter:serp:xyz")) is None

    def test_corrupted_json_treated_as_miss(self):
        fake = _fake_redis()
        fake.get.return_value = "not-json{{{"
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_get("hunter:serp:bad")) is None

    def test_non_dict_payload_treated_as_miss(self):
        fake = _fake_redis()
        fake.get.return_value = json.dumps(["list", "not", "dict"])
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_get("hunter:serp:arr")) is None

    def test_redis_raises_returns_none(self):
        fake = _fake_redis()
        fake.get.side_effect = RuntimeError("connection reset")
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_get("hunter:serp:boom")) is None  # no crash


# ─────────────────────────────────────────────────────
# cache_set — writes with TTL, silent on failure
# ─────────────────────────────────────────────────────
class TestCacheSet:
    def test_set_uses_default_ttl(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake), \
             patch.object(cache_module.settings, "CACHE_TTL_DAYS", 30):
            ok = _run(cache_set("hunter:serp:k", {"a": 1}))

        assert ok is True
        fake.setex.assert_called_once()
        key, ttl, payload = fake.setex.call_args[0]
        assert key == "hunter:serp:k"
        assert ttl == 30 * 86400
        assert json.loads(payload) == {"a": 1}

    def test_set_respects_custom_ttl(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake):
            _run(cache_set("hunter:x:y", {"a": 1}, ttl=120))
        _, ttl, _ = fake.setex.call_args[0]
        assert ttl == 120

    def test_set_falls_back_to_default_when_ttl_invalid(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake), \
             patch.object(cache_module.settings, "CACHE_TTL_DAYS", 7):
            _run(cache_set("hunter:x:y", {"a": 1}, ttl=0))
        _, ttl, _ = fake.setex.call_args[0]
        assert ttl == 7 * 86400

    def test_set_redis_unavailable_returns_false(self):
        with patch.object(cache_module, "get_redis", return_value=None):
            assert _run(cache_set("hunter:x:y", {"a": 1})) is False

    def test_set_non_dict_returns_false(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_set("hunter:x:y", "not a dict")) is False  # type: ignore[arg-type]
        fake.setex.assert_not_called()

    def test_set_serialises_datetime_via_default_str(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake):
            ok = _run(cache_set(
                "hunter:x:y",
                {"at": datetime(2026, 4, 8, 12, 0, 0)},
            ))
        assert ok is True
        _, _, payload = fake.setex.call_args[0]
        assert "2026-04-08" in payload

    def test_set_redis_raises_returns_false(self):
        fake = _fake_redis()
        fake.setex.side_effect = RuntimeError("boom")
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(cache_set("hunter:x:y", {"a": 1})) is False

    def test_cache_set_ttl_alias_is_same_function(self):
        assert cache_set_ttl is cache_set


# ─────────────────────────────────────────────────────
# is_cached / invalidate_key
# ─────────────────────────────────────────────────────
class TestExistsAndInvalidate:
    def test_is_cached_true(self):
        fake = _fake_redis()
        fake.exists.return_value = 1
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(is_cached("hunter:x:y")) is True

    def test_is_cached_false(self):
        fake = _fake_redis()
        fake.exists.return_value = 0
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(is_cached("hunter:x:y")) is False

    def test_is_cached_no_redis(self):
        with patch.object(cache_module, "get_redis", return_value=None):
            assert _run(is_cached("hunter:x:y")) is False

    def test_invalidate_key_removes(self):
        fake = _fake_redis()
        fake.delete.return_value = 1
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(invalidate_key("hunter:x:y")) is True
        fake.delete.assert_called_once_with("hunter:x:y")

    def test_invalidate_key_miss(self):
        fake = _fake_redis()
        fake.delete.return_value = 0
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(invalidate_key("hunter:x:y")) is False


# ─────────────────────────────────────────────────────
# invalidate_pattern — SCAN + DEL batching, safety rail
# ─────────────────────────────────────────────────────
class TestInvalidatePattern:
    def test_refuses_wildcard_only(self):
        fake = _fake_redis()
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(invalidate_pattern("*")) == 0
            assert _run(invalidate_pattern("")) == 0
        fake.scan.assert_not_called()
        fake.delete.assert_not_called()

    def test_scans_and_deletes_batches(self):
        fake = _fake_redis()
        # First scan returns a batch + cursor=42, second returns final batch + cursor=0
        fake.scan.side_effect = [
            (42, ["hunter:serp:a", "hunter:serp:b"]),
            (0, ["hunter:serp:c"]),
        ]
        fake.delete.side_effect = [2, 1]

        with patch.object(cache_module, "get_redis", return_value=fake):
            removed = _run(invalidate_pattern("hunter:serp:*"))

        assert removed == 3
        assert fake.scan.call_count == 2
        assert fake.delete.call_count == 2

    def test_no_redis_returns_zero(self):
        with patch.object(cache_module, "get_redis", return_value=None):
            assert _run(invalidate_pattern("hunter:serp:*")) == 0

    def test_scan_raises_returns_zero(self):
        fake = _fake_redis()
        fake.scan.side_effect = RuntimeError("boom")
        with patch.object(cache_module, "get_redis", return_value=fake):
            assert _run(invalidate_pattern("hunter:serp:*")) == 0
