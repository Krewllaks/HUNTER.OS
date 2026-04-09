"""
Tests for app.services.enrichment.apollo_client.

All HTTP traffic is mocked via ``unittest.mock`` patches on
``httpx.AsyncClient``. No real Apollo request is ever sent.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.enrichment import apollo_client as ap_module
from app.services.enrichment.apollo_client import ApolloClient


def _run(coro):
    return asyncio.run(coro)


def _build_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock(name=f"Response<{status_code}>")
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    return resp


def _patched_async_client(post_returns):
    fake_client = MagicMock(name="FakeHTTPClient")
    if isinstance(post_returns, list):
        fake_client.post = AsyncMock(side_effect=post_returns)
    else:
        fake_client.post = AsyncMock(return_value=post_returns)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_client)
    cm.__aexit__ = AsyncMock(return_value=None)

    cls = MagicMock(return_value=cm)
    return patch.object(ap_module.httpx, "AsyncClient", cls), fake_client


# ─────────────────────────────────────────────────────
# Disabled / input validation
# ─────────────────────────────────────────────────────
class TestApolloDisabled:
    def test_no_api_key_returns_none(self):
        client = ApolloClient(api_key=None)
        assert _run(client.find_email("Ahmet", "Yilmaz", "acme.com.tr")) is None

    def test_missing_first_name_returns_none(self):
        client = ApolloClient(api_key="k")
        assert _run(client.find_email("", "Yilmaz", "acme.com.tr")) is None

    def test_missing_last_name_returns_none(self):
        client = ApolloClient(api_key="k")
        assert _run(client.find_email("Ahmet", "   ", "acme.com.tr")) is None

    def test_missing_domain_returns_none(self):
        client = ApolloClient(api_key="k")
        assert _run(client.find_email("Ahmet", "Yilmaz", "")) is None


# ─────────────────────────────────────────────────────
# Cache hit short-circuits
# ─────────────────────────────────────────────────────
class TestApolloCache:
    def test_cache_hit_returns_without_http(self):
        cached = {"email": "ahmet@acme.com.tr", "source": "apollo"}
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()), \
             patch.object(ap_module.httpx, "AsyncClient") as fake_cls:
            client = ApolloClient(api_key="k")
            result = _run(client.find_email("Ahmet", "Yilmaz", "acme.com.tr"))

        assert result == cached
        fake_cls.assert_not_called()


# ─────────────────────────────────────────────────────
# Successful response parsing
# ─────────────────────────────────────────────────────
class TestApolloSuccess:
    def test_parses_person_match(self):
        payload = {
            "person": {
                "email": "ahmet@acme.com.tr",
                "title": "CTO",
                "linkedin_url": "https://linkedin.com/in/ahmet",
                "first_name": "Ahmet",
                "last_name": "Yilmaz",
                "organization": {"name": "Acme Yazilim"},
            }
        }
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()) as set_mock:
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                client = ApolloClient(api_key="k")
                result = _run(client.find_email("Ahmet", "Yilmaz", "acme.com.tr"))

        assert result is not None
        assert result["email"] == "ahmet@acme.com.tr"
        assert result["title"] == "CTO"
        assert result["company"] == "Acme Yazilim"
        assert result["source"] == "apollo"
        set_mock.assert_called_once()

    def test_person_without_email_returns_none(self):
        payload = {"person": {"title": "CTO", "first_name": "X"}}
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()) as set_mock:
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None
        set_mock.assert_not_called()

    def test_no_person_field_returns_none(self):
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(200, {}))
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None


# ─────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────
class TestApolloErrors:
    def test_401_returns_none(self):
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(401, text="invalid key"))
            with patcher:
                result = _run(ApolloClient(api_key="bad").find_email("A", "B", "c.com"))
        assert result is None

    def test_429_returns_none(self):
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(429))
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None

    def test_5xx_returns_none(self):
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(503, text="boom"))
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None

    def test_network_error_returns_none(self):
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client([httpx.TimeoutException("boom")])
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None

    def test_non_json_returns_none(self):
        resp = _build_response(200)
        resp.json = MagicMock(side_effect=ValueError("not json"))
        with patch.object(ap_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ap_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(resp)
            with patcher:
                result = _run(ApolloClient(api_key="k").find_email("A", "B", "c.com"))
        assert result is None
