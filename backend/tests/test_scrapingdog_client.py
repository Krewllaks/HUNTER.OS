"""
Tests for app.services.serp.scrapingdog_client.

All HTTP traffic is mocked via ``unittest.mock.patch`` on
``httpx.AsyncClient``. No real ScrapingDog request is ever sent.
Cache is mocked through ``app.services.serp.scrapingdog_client.cache_get/set``.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.serp import scrapingdog_client as sdc_module
from app.services.serp.scrapingdog_client import ScrapingDogClient


def _run(coro):
    return asyncio.run(coro)


def _build_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    """Create a fake httpx.Response."""
    resp = MagicMock(name=f"Response<{status_code}>")
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    return resp


def _patched_async_client(get_returns):
    """
    Build a patcher for httpx.AsyncClient whose .get() returns/raises
    according to ``get_returns`` (single value or list of side_effects).
    """
    fake_client = MagicMock(name="FakeHTTPClient")
    if isinstance(get_returns, list):
        fake_client.get = AsyncMock(side_effect=get_returns)
    else:
        fake_client.get = AsyncMock(return_value=get_returns)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_client)
    cm.__aexit__ = AsyncMock(return_value=None)

    cls = MagicMock(return_value=cm)
    return patch.object(sdc_module.httpx, "AsyncClient", cls), fake_client


# ─────────────────────────────────────────────────────
# Disabled / input validation
# ─────────────────────────────────────────────────────
class TestScrapingDogDisabled:
    def test_no_api_key_returns_none(self):
        client = ScrapingDogClient(api_key=None)
        assert _run(client.search("anything")) is None

    def test_empty_query_returns_none(self):
        client = ScrapingDogClient(api_key="test")
        assert _run(client.search("")) is None
        assert _run(client.search("   ")) is None


# ─────────────────────────────────────────────────────
# Cache hit short-circuits the API
# ─────────────────────────────────────────────────────
class TestScrapingDogCache:
    def test_cache_hit_returns_without_http(self):
        cached_payload = {
            "results": [{"title": "T", "url": "https://x", "snippet": "S", "position": 1}],
            "query": "foo",
        }
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=cached_payload)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.httpx, "AsyncClient") as fake_cls:
            client = ScrapingDogClient(api_key="k")
            results = _run(client.search("foo"))

        assert results == cached_payload["results"]
        fake_cls.assert_not_called()  # never opened an HTTP client


# ─────────────────────────────────────────────────────
# Successful response parsing
# ─────────────────────────────────────────────────────
class TestScrapingDogSuccess:
    def test_parses_organic_results(self):
        payload = {
            "organic_results": [
                {"title": "Acme", "link": "https://acme.com", "snippet": "Acme Inc.", "position": 1},
                {"title": "Beta", "link": "https://beta.com", "snippet": "Beta Co.", "position": 2},
            ]
        }
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()) as set_mock:
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                client = ScrapingDogClient(api_key="k")
                results = _run(client.search("acme"))

        assert results is not None
        assert len(results) == 2
        assert results[0]["title"] == "Acme"
        assert results[0]["url"] == "https://acme.com"
        assert results[0]["snippet"] == "Acme Inc."
        # Cache write happened with normalised payload
        set_mock.assert_called_once()
        cached_arg = set_mock.call_args[0][1]
        assert "results" in cached_arg

    def test_accepts_organic_data_alias(self):
        """Some ScrapingDog plans return organic_data instead of organic_results."""
        payload = {
            "organic_data": [
                {"title": "X", "url": "https://x.com", "description": "desc"},
            ]
        }
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                client = ScrapingDogClient(api_key="k")
                results = _run(client.search("x"))

        assert results == [{
            "title": "X", "url": "https://x.com", "snippet": "desc", "position": 1,
        }]

    def test_skips_items_without_url(self):
        payload = {"organic_results": [
            {"title": "no url", "snippet": "x"},
            {"title": "ok", "url": "https://ok.com"},
        ]}
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))

        assert results == [{
            "title": "ok", "url": "https://ok.com", "snippet": "", "position": 2,
        }]

    def test_empty_organic_results_returns_none(self):
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()) as set_mock:
            patcher, _ = _patched_async_client(_build_response(200, {"organic_results": []}))
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("x"))

        assert results is None
        set_mock.assert_not_called()  # never cache a miss


# ─────────────────────────────────────────────────────
# Rate limiting / retry / failure
# ─────────────────────────────────────────────────────
class TestScrapingDogRetry:
    def test_429_then_success_retries_with_backoff(self):
        responses = [
            _build_response(429, text="rate limited"),
            _build_response(200, {"organic_results": [
                {"title": "T", "url": "https://t.com", "snippet": "s"}
            ]}),
        ]
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.asyncio, "sleep", new=AsyncMock()) as sleep_mock:
            patcher, _ = _patched_async_client(responses)
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))

        assert results is not None
        assert len(results) == 1
        sleep_mock.assert_awaited()  # backoff happened

    def test_persistent_429_returns_none(self):
        responses = [_build_response(429) for _ in range(10)]
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.asyncio, "sleep", new=AsyncMock()):
            patcher, _ = _patched_async_client(responses)
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))
        assert results is None

    def test_4xx_other_returns_none_immediately(self):
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.asyncio, "sleep", new=AsyncMock()) as sleep_mock:
            patcher, _ = _patched_async_client(_build_response(403, text="forbidden"))
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))
        assert results is None
        sleep_mock.assert_not_awaited()  # no retry on hard 4xx

    def test_5xx_then_success(self):
        responses = [
            _build_response(503),
            _build_response(200, {"organic_results": [
                {"title": "T", "url": "https://t.com"}
            ]}),
        ]
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.asyncio, "sleep", new=AsyncMock()):
            patcher, _ = _patched_async_client(responses)
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))
        assert results is not None and len(results) == 1

    def test_network_error_returns_none(self):
        with patch.object(sdc_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(sdc_module, "cache_set", new=AsyncMock()), \
             patch.object(sdc_module.asyncio, "sleep", new=AsyncMock()):
            patcher, _ = _patched_async_client([httpx.TimeoutException("boom")] * 10)
            with patcher:
                results = _run(ScrapingDogClient(api_key="k").search("q"))
        assert results is None
