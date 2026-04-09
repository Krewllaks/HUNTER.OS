"""
Tests for app.services.enrichment.pdl_client.

PDL is a profile enricher (NOT an email finder). All HTTP traffic
is mocked. No real PDL request is ever sent.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.enrichment import pdl_client as pdl_module
from app.services.enrichment.pdl_client import PDLClient


def _run(coro):
    return asyncio.run(coro)


def _build_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock(name=f"Response<{status_code}>")
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    return resp


def _patched_async_client(get_returns):
    fake_client = MagicMock(name="FakeHTTPClient")
    if isinstance(get_returns, list):
        fake_client.get = AsyncMock(side_effect=get_returns)
    else:
        fake_client.get = AsyncMock(return_value=get_returns)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_client)
    cm.__aexit__ = AsyncMock(return_value=None)

    cls = MagicMock(return_value=cm)
    return patch.object(pdl_module.httpx, "AsyncClient", cls), fake_client


# ─────────────────────────────────────────────────────
# Disabled / input validation
# ─────────────────────────────────────────────────────
class TestPDLDisabled:
    def test_no_api_key_returns_none(self):
        client = PDLClient(api_key=None)
        assert _run(client.enrich_person(email="a@b.com")) is None

    def test_no_email_or_linkedin_returns_none(self):
        client = PDLClient(api_key="k")
        assert _run(client.enrich_person()) is None
        assert _run(client.enrich_person(email="", linkedin_url="")) is None


# ─────────────────────────────────────────────────────
# Cache hit
# ─────────────────────────────────────────────────────
class TestPDLCache:
    def test_cache_hit_returns_without_http(self):
        cached = {"job_title": "CTO", "source": "pdl"}
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()), \
             patch.object(pdl_module.httpx, "AsyncClient") as fake_cls:
            client = PDLClient(api_key="k")
            result = _run(client.enrich_person(email="a@b.com"))

        assert result == cached
        fake_cls.assert_not_called()


# ─────────────────────────────────────────────────────
# Successful enrichment
# ─────────────────────────────────────────────────────
class TestPDLSuccess:
    def test_parses_data_field(self):
        payload = {
            "data": {
                "job_title": "Chief Technology Officer",
                "job_company_name": "Acme Yazilim",
                "job_company_size": "11-50",
                "linkedin_url": "linkedin.com/in/ahmet",
                "skills": ["python", "leadership"],
                "interests": ["startups"],
                "summary": "CTO at Acme",
                "location_country": "turkey",
            }
        }
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()) as set_mock:
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="ahmet@acme.com.tr"))

        assert result is not None
        assert result["job_title"] == "Chief Technology Officer"
        assert result["job_company_name"] == "Acme Yazilim"
        assert result["skills"] == ["python", "leadership"]
        assert result["source"] == "pdl"
        set_mock.assert_called_once()

    def test_drops_falsy_fields(self):
        payload = {"data": {"job_title": "CTO", "skills": [], "summary": None}}
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(200, payload))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is not None
        assert "summary" not in result
        # skills was empty list → dropped
        assert "skills" not in result or result["skills"]
        assert result["job_title"] == "CTO"

    def test_empty_data_returns_none(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(200, {"data": None}))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is None


# ─────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────
class TestPDLErrors:
    def test_401_returns_none(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(401))
            with patcher:
                result = _run(PDLClient(api_key="bad").enrich_person(email="x@y.com"))
        assert result is None

    def test_402_free_tier_exhausted(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(402))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is None

    def test_404_no_match(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(404))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is None

    def test_429_returns_none(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client(_build_response(429))
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is None

    def test_network_error_returns_none(self):
        with patch.object(pdl_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(pdl_module, "cache_set", new=AsyncMock()):
            patcher, _ = _patched_async_client([httpx.TimeoutException("boom")])
            with patcher:
                result = _run(PDLClient(api_key="k").enrich_person(email="x@y.com"))
        assert result is None
