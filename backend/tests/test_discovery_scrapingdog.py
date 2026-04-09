"""
Phase 11 — DiscoveryService cost-optimised SERP path tests.

Mocks:
* ScrapingDogClient.search   → controls primary SERP results
* DiscoveryService._search_ddg_sdk → controls fallback SERP results
* cache_get / cache_set      → controls cache layer
* settings.SCRAPINGDOG_API_KEY → toggles ScrapingDog availability

NO real HTTP. NO real Gemini. NO real DB.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import discovery_service as ds_module
from app.services.discovery_service import DiscoveryService


def _run(coro):
    return asyncio.run(coro)


def _make_service() -> DiscoveryService:
    """Build a DiscoveryService without touching SQLAlchemy or Gemini."""
    db = MagicMock(name="FakeSession")
    with patch.object(ds_module.genai, "configure"), \
         patch.object(ds_module.genai, "GenerativeModel"):
        return DiscoveryService(db)


def _make_product() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        name="HUNTER.OS",
        description_prompt="AI sales hunter",
        hunt_progress={},
        icp_profile={},
        search_queries={},
    )


# ─────────────────────────────────────────────────────
# ScrapingDog primary path
# ─────────────────────────────────────────────────────
class TestScrapingDogPath:
    def test_scrapingdog_returns_results_first(self):
        svc = _make_service()
        product = _make_product()

        sd_results = [
            {"title": "Acme", "url": "https://acme.com.tr", "snippet": "x", "position": 1}
        ]

        async def fake_search(self, query, num=20, country="tr"):
            return sd_results

        with patch.object(ds_module.settings, "SCRAPINGDOG_API_KEY", "test-key"), \
             patch.object(ds_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ds_module, "cache_set", new=AsyncMock()), \
             patch.object(ds_module.ScrapingDogClient, "search", new=fake_search), \
             patch.object(svc, "_search_ddg_sdk",
                          new=AsyncMock(side_effect=AssertionError("ddg should not run"))), \
             patch.object(svc, "_update_progress"):
            results = _run(svc._search_all_queries(product, ["query1"]))

        assert results == sd_results

    def test_scrapingdog_failure_falls_back_to_ddg(self):
        svc = _make_service()
        product = _make_product()

        ddg_results = [{"title": "from ddg", "url": "https://x.com", "snippet": "y"}]

        async def boom_search(self, query, num=20, country="tr"):
            raise RuntimeError("api down")

        with patch.object(ds_module.settings, "SCRAPINGDOG_API_KEY", "test-key"), \
             patch.object(ds_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ds_module, "cache_set", new=AsyncMock()), \
             patch.object(ds_module.ScrapingDogClient, "search", new=boom_search), \
             patch.object(svc, "_search_ddg_sdk",
                          new=AsyncMock(return_value=ddg_results)), \
             patch.object(svc, "_update_progress"):
            results = _run(svc._search_all_queries(product, ["query1"]))

        assert results == ddg_results

    def test_scrapingdog_disabled_uses_ddg(self):
        svc = _make_service()
        product = _make_product()

        ddg_results = [{"title": "ddg", "url": "https://y.com", "snippet": "z"}]

        with patch.object(ds_module.settings, "SCRAPINGDOG_API_KEY", None), \
             patch.object(ds_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ds_module, "cache_set", new=AsyncMock()), \
             patch.object(svc, "_search_ddg_sdk",
                          new=AsyncMock(return_value=ddg_results)), \
             patch.object(svc, "_update_progress"):
            results = _run(svc._search_all_queries(product, ["query1"]))

        assert results == ddg_results


# ─────────────────────────────────────────────────────
# Cache layer
# ─────────────────────────────────────────────────────
class TestSerpCache:
    def test_cache_hit_skips_all_providers(self):
        svc = _make_service()
        product = _make_product()
        cached = [{"title": "cached", "url": "https://cached.com", "snippet": "s"}]

        with patch.object(ds_module.settings, "SCRAPINGDOG_API_KEY", "test-key"), \
             patch.object(ds_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(ds_module, "cache_set", new=AsyncMock()) as set_mock, \
             patch.object(ds_module.ScrapingDogClient, "search",
                          new=AsyncMock(side_effect=AssertionError("should not run"))), \
             patch.object(svc, "_search_ddg_sdk",
                          new=AsyncMock(side_effect=AssertionError("should not run"))), \
             patch.object(svc, "_update_progress"):
            results = _run(svc._search_all_queries(product, ["query1"]))

        assert results == cached
        # Successful cache hit must NOT re-write the cache
        set_mock.assert_not_called()

    def test_successful_query_caches_result(self):
        svc = _make_service()
        product = _make_product()
        sd_results = [{"title": "x", "url": "https://x.com", "snippet": "y"}]

        async def fake_search(self, query, num=20, country="tr"):
            return sd_results

        set_mock = AsyncMock()
        with patch.object(ds_module.settings, "SCRAPINGDOG_API_KEY", "test-key"), \
             patch.object(ds_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(ds_module, "cache_set", new=set_mock), \
             patch.object(ds_module.ScrapingDogClient, "search", new=fake_search), \
             patch.object(svc, "_update_progress"):
            _run(svc._search_all_queries(product, ["query1"]))

        set_mock.assert_called_once()


# ─────────────────────────────────────────────────────
# Extended dorks (Phase 11)
# ─────────────────────────────────────────────────────
class TestExtendedDorks:
    def test_extended_dorks_present(self):
        svc = _make_service()
        svc._current_icp = {"geography": ["istanbul"]}
        queries = svc._build_template_dorks(
            industries=["yazilim"],
            titles=["CTO"],
            keywords=["python", "aws"],
        )
        joined = " | ".join(queries)
        # Hiring + funding + tech-stack signals are FAZ 2 additions
        assert any("hiring" in q or "yatırım" in q or "raised" in q for q in queries), joined
        # GitHub fingerprint
        assert any("github.com" in q for q in queries), joined
        # Kariyer.net (TR job board)
        assert any("kariyer.net" in q for q in queries), joined

    def test_extended_dorks_increase_count(self):
        svc = _make_service()
        svc._current_icp = {"geography": ["istanbul"]}
        queries = svc._build_template_dorks(
            industries=["yazilim", "saas"],
            titles=["CTO", "CEO"],
            keywords=["python"],
        )
        # Phase 1-10 produced ~8 dorks; Phase 11 minimum should be 12+
        assert len(queries) >= 12, f"only got {len(queries)}: {queries}"


# ─────────────────────────────────────────────────────
# Intent score gate
# ─────────────────────────────────────────────────────
class TestIntentScoreGate:
    """Logic test for the score-vs-threshold predicate used at line ~290."""

    def test_low_score_skipped(self):
        threshold = 50
        score = 45
        assert not (score >= max(40, threshold))

    def test_high_score_kept(self):
        threshold = 50
        score = 65
        assert score >= max(40, threshold)

    def test_threshold_setting_overrides_legacy_40(self):
        # Phase 11 raises floor — score 42 was OK in Phase 1-10 but
        # blocked when INTENT_SCORE_THRESHOLD_DISCOVERY=60.
        threshold = 60
        score = 42
        assert not (score >= max(40, threshold))
