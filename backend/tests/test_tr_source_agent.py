"""
Tests for app.services.scout.tr_source_agent.

All HTML fetching is mocked via patching ``_fetch_html`` directly,
so no real Playwright/httpx call is ever made.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.scout import tr_source_agent as tr_module
from app.services.scout.tr_source_agent import TRSourceAgent


def _run(coro):
    return asyncio.run(coro)


_TOBB_HTML = """
<html><body>
  <a href="https://uye.tobb.org.tr/firma/123">Acme Yazilim A.S.</a>
  <a href="https://google.com">unrelated</a>
  <a href="https://uye.tobb.org.tr/firma/456">Acme Teknoloji</a>
</body></html>
"""

_KOSGEB_HTML = """
<html><body>
  <a href="https://www.kosgeb.gov.tr/site/tr/firma/1">SME Co</a>
</body></html>
"""

_CHAMBER_HTML = """
<html><body>
  <a href="https://www.ito.org.tr/uye/789">ITO Member</a>
</body></html>
"""

_NIC_HTML = """
<html><body>
  <a href="https://acme.com.tr">acme.com.tr</a>
  <a href="https://other.com">other.com</a>
</body></html>
"""

_KARIYER_HTML = """
<html><body>
  <a href="https://www.kariyer.net/is-ilanlari/cto-istanbul">CTO Istanbul</a>
</body></html>
"""


# ─────────────────────────────────────────────────────
# Input validation
# ─────────────────────────────────────────────────────
class TestTRInputValidation:
    def test_search_tobb_empty(self):
        assert _run(TRSourceAgent().search_tobb("")) == []
        assert _run(TRSourceAgent().search_tobb("   ")) == []

    def test_search_kosgeb_missing(self):
        assert _run(TRSourceAgent().search_kosgeb("", "istanbul")) == []
        assert _run(TRSourceAgent().search_kosgeb("yazilim", "")) == []

    def test_scan_com_tr_empty(self):
        assert _run(TRSourceAgent().scan_com_tr_domains("")) == []

    def test_scan_kariyer_empty(self):
        assert _run(TRSourceAgent().scan_kariyer_net("")) == []


# ─────────────────────────────────────────────────────
# Cache hit short-circuits HTTP
# ─────────────────────────────────────────────────────
class TestTRCache:
    def test_tobb_cache_hit(self):
        cached = {"results": [{"title": "cached", "url": "u", "source": "tobb",
                                "country": "TR", "snippet": "x", "extra": {}}]}
        with patch.object(tr_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(tr_module, "cache_set", new=AsyncMock()), \
             patch.object(TRSourceAgent, "_fetch_html", new=AsyncMock()) as fetch_mock:
            agent = TRSourceAgent()
            result = _run(agent.search_tobb("acme"))
        assert result == cached["results"]
        fetch_mock.assert_not_called()


# ─────────────────────────────────────────────────────
# Successful HTML parsing per source
# ─────────────────────────────────────────────────────
class TestTRSources:
    def _run_with_html(self, method_name: str, html: str, *args):
        with patch.object(tr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(tr_module, "cache_set", new=AsyncMock()), \
             patch.object(TRSourceAgent, "_fetch_html", new=AsyncMock(return_value=html)):
            agent = TRSourceAgent()
            return _run(getattr(agent, method_name)(*args))

    def test_tobb_parses_results(self):
        results = self._run_with_html("search_tobb", _TOBB_HTML, "acme")
        assert len(results) == 2
        assert all(r["source"] == "tobb" for r in results)
        assert all(r["country"] == "TR" for r in results)
        assert all("uye.tobb.org.tr" in r["url"] for r in results)

    def test_kosgeb_parses_results(self):
        results = self._run_with_html("search_kosgeb", _KOSGEB_HTML, "yazilim", "istanbul")
        assert len(results) == 1
        assert results[0]["source"] == "kosgeb"

    def test_chamber_parses_results(self):
        results = self._run_with_html("search_chamber", _CHAMBER_HTML, "istanbul")
        assert len(results) == 1
        assert results[0]["source"] == "chamber_ito"

    def test_chamber_unknown_city_falls_back_to_istanbul(self):
        results = self._run_with_html("search_chamber", _CHAMBER_HTML, "mars")
        assert len(results) == 1
        assert results[0]["source"] == "chamber_ito"

    def test_nic_tr_parses_results(self):
        results = self._run_with_html("scan_com_tr_domains", _NIC_HTML, "acme")
        assert len(results) == 1
        assert results[0]["source"] == "nic_tr"
        assert ".com.tr" in results[0]["url"]

    def test_kariyer_parses_results(self):
        results = self._run_with_html("scan_kariyer_net", _KARIYER_HTML, "cto")
        assert len(results) == 1
        assert results[0]["source"] == "kariyer_net"

    def test_empty_html_returns_empty(self):
        results = self._run_with_html("search_tobb", None, "acme")
        assert results == []


# ─────────────────────────────────────────────────────
# discover_all aggregator
# ─────────────────────────────────────────────────────
class TestTRDiscoverAll:
    def test_discover_all_no_inputs(self):
        with patch.object(TRSourceAgent, "_fetch_html", new=AsyncMock()):
            assert _run(TRSourceAgent().discover_all()) == []

    def test_discover_all_aggregates(self):
        async def fake_fetch(self, url, requires_js):
            if "tobb" in url:
                return _TOBB_HTML
            if "kosgeb" in url:
                return _KOSGEB_HTML
            if "ito" in url or "atonet" in url or "izto" in url:
                return _CHAMBER_HTML
            if "nic.tr" in url:
                return _NIC_HTML
            if "kariyer.net" in url:
                return _KARIYER_HTML
            return None

        with patch.object(tr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(tr_module, "cache_set", new=AsyncMock()), \
             patch.object(TRSourceAgent, "_fetch_html", new=fake_fetch):
            results = _run(TRSourceAgent().discover_all(
                company_name="acme",
                industry="yazilim",
                city="istanbul",
                title="cto",
            ))

        sources = {r["source"] for r in results}
        # All five source types should appear at least once.
        assert "tobb" in sources
        assert "kosgeb" in sources
        assert "chamber_ito" in sources
        assert "nic_tr" in sources
        assert "kariyer_net" in sources

    def test_discover_all_swallows_exceptions(self):
        async def boom_fetch(self, url, requires_js):
            raise RuntimeError("network down")

        with patch.object(tr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(tr_module, "cache_set", new=AsyncMock()), \
             patch.object(TRSourceAgent, "_fetch_html", new=boom_fetch):
            # Should not raise; just returns empty.
            results = _run(TRSourceAgent().discover_all(
                company_name="acme", city="istanbul"
            ))
        assert results == []


# ─────────────────────────────────────────────────────
# IPRoyal proxy URL builder
# ─────────────────────────────────────────────────────
class TestIProyalProxy:
    def test_no_creds_returns_none(self):
        with patch.object(tr_module.settings, "IPROYAL_USERNAME", None), \
             patch.object(tr_module.settings, "IPROYAL_PASSWORD", None):
            assert TRSourceAgent()._build_iproyal_proxy_url() is None

    def test_builds_sticky_session_url(self):
        with patch.object(tr_module.settings, "IPROYAL_USERNAME", "user1"), \
             patch.object(tr_module.settings, "IPROYAL_PASSWORD", "pass1"), \
             patch.object(tr_module.settings, "IPROYAL_ENDPOINT", "geo.iproyal.com:12321"), \
             patch.object(tr_module.settings, "IPROYAL_POOL_SIZE", 5):
            url = TRSourceAgent()._build_iproyal_proxy_url()
        assert url is not None
        assert url.startswith("http://user1-session-")
        assert "-country-tr:pass1@geo.iproyal.com:12321" in url
