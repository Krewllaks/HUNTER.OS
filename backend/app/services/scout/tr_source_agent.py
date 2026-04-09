"""
HUNTER.OS - Türkiye Source Agent (Phase 11) ⭐
================================================
THE TURKEY-SPECIFIC LEAD SOURCE AGENT.

This file is the main competitive moat against Apollo / Clay /
Lemlist / Outreach in the Türkiye market. None of those tools index
TOBB, KOSGEB, local Chambers of Commerce, .com.tr WHOIS, or
Kariyer.net job postings — but Turkish marketing agencies live and
die by exactly that data.

What it does
------------
Each public method scrapes a single TR data source and returns a
list of dicts shaped to be drop-in compatible with
``DiscoveryService._analyze_and_extract`` (``{"title", "url",
"snippet"}`` plus extra metadata).

* :meth:`search_tobb` — TOBB (Türkiye Odalar ve Borsalar Birliği)
  member directory.
* :meth:`search_kosgeb` — KOSGEB-supported SMEs by industry / city.
* :meth:`search_chamber` — local Chamber of Commerce member rolls
  (ITO Istanbul, ATO Ankara, IZTO Izmir, ...).
* :meth:`scan_com_tr_domains` — public ``.com.tr`` domain WHOIS /
  registry intelligence.
* :meth:`scan_kariyer_net` — Kariyer.net job postings, used as a
  high-confidence hiring signal.

Stealth & cost
--------------
* All HTTP traffic goes through :class:`StealthBrowser` (or plain
  ``httpx`` for static pages) routed via the IPRoyal residential
  proxy pool with TR exit IPs (kritik — bazı siteler yurt dışı
  IP'lere kapalı).
* Every method caches results for ``CACHE_TTL_DAYS`` (default 30
  days) via the Phase 11 cache layer, so re-running the same hunt
  costs zero proxy bandwidth and zero browser launches.

Failure mode
------------
Any individual source can return an empty list without breaking the
agent. Errors are logged and swallowed — DiscoveryService just gets
fewer leads from that one source. Never raises.
"""
from __future__ import annotations

import logging
import random
import urllib.parse
from typing import Any, Optional

import httpx

from app.core.cache import cache_get, cache_key, cache_set
from app.core.config import settings

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


class TRSourceAgent:
    """
    Aggregator over Türkiye-specific public lead sources.

    All public methods are async and return ``list[dict]`` with the
    DiscoveryService-compatible shape::

        {
            "title":   str,   # human-readable source name
            "url":     str,   # canonical URL of the lead/profile
            "snippet": str,   # one-line description
            "source":  str,   # which TR source produced this
            "country": "TR",  # always Türkiye
            "extra":   dict,  # source-specific metadata
        }
    """

    def __init__(self, use_stealth: bool = True) -> None:
        # Lazy-import StealthBrowser so the module is importable in
        # environments where Playwright isn't installed (e.g. CI test
        # runner). The class is only resolved when actually used.
        self.use_stealth = use_stealth
        self._stealth_cls = None

    # ─────────────────────────────────────────────────────
    # Public sources
    # ─────────────────────────────────────────────────────

    async def search_tobb(self, company_name: str) -> list[dict[str, Any]]:
        """
        Search TOBB's public member directory by company name.

        Parameters
        ----------
        company_name : str
            Free-text company name (e.g. ``"Acme Yazılım"``).

        Returns
        -------
        list[dict]
            DiscoveryService-compatible result list. Empty on miss.
        """
        if not company_name or not company_name.strip():
            return []

        ck = cache_key("tr_tobb", company_name)
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            return cached["results"]

        # TOBB exposes a public search at https://uye.tobb.org.tr/
        url = f"https://uye.tobb.org.tr/firma/?q={urllib.parse.quote(company_name)}"
        html = await self._fetch_html(url, requires_js=True)
        results = self._parse_tobb_html(html, company_name) if html else []

        await cache_set(ck, {"results": results, "query": company_name})
        return results

    async def search_kosgeb(self, industry: str, city: str) -> list[dict[str, Any]]:
        """
        Find KOSGEB-supported SMEs filtered by industry and city.

        KOSGEB (Küçük ve Orta Ölçekli İşletmeleri Geliştirme ve
        Destekleme İdaresi) periodically publishes lists of supported
        companies — those companies are funded, growing, and uniquely
        valuable as outreach targets.
        """
        if not (industry and city):
            return []

        ck = cache_key("tr_kosgeb", industry, city)
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            return cached["results"]

        url = (
            "https://www.kosgeb.gov.tr/site/tr/genel/destekdetay/"
            f"?q={urllib.parse.quote(industry)}&il={urllib.parse.quote(city)}"
        )
        html = await self._fetch_html(url, requires_js=True)
        results = self._parse_kosgeb_html(html, industry, city) if html else []

        await cache_set(ck, {"results": results, "query": f"{industry}|{city}"})
        return results

    async def search_chamber(self, city: str = "istanbul") -> list[dict[str, Any]]:
        """
        Crawl the local Chamber of Commerce member roll for a TR city.

        Supported cities: ``istanbul`` (ITO), ``ankara`` (ATO),
        ``izmir`` (IZTO). Falls back to ITO for unknown values.
        """
        chamber_map = {
            "istanbul": ("ITO", "https://www.ito.org.tr/tr/uye-bilgi-sistemi"),
            "ankara":   ("ATO", "https://www.atonet.org.tr/uye-bilgi-sistemi"),
            "izmir":    ("IZTO", "https://www.izto.org.tr/tr/uye-bilgi-sistemi"),
        }
        key = (city or "istanbul").strip().lower()
        chamber_name, url = chamber_map.get(key, chamber_map["istanbul"])

        ck = cache_key("tr_chamber", chamber_name, key)
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            return cached["results"]

        html = await self._fetch_html(url, requires_js=True)
        results = self._parse_chamber_html(html, chamber_name, key) if html else []

        await cache_set(ck, {"results": results, "city": key})
        return results

    async def scan_com_tr_domains(self, keyword: str) -> list[dict[str, Any]]:
        """
        Search the ``.com.tr`` registry for domains matching a keyword.

        ``.com.tr`` registration is gated (requires Turkish trade
        registry docs) so every match is a verified Türkiye-based
        business — much higher signal than ``.com``.
        """
        if not keyword or not keyword.strip():
            return []

        ck = cache_key("tr_comtr", keyword)
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            return cached["results"]

        # nic.tr publishes a public WHOIS web search
        url = f"https://www.nic.tr/index.php?USRACTN=DOMAINSRCH&DOMAINNAME={urllib.parse.quote(keyword)}"
        html = await self._fetch_html(url, requires_js=False)
        results = self._parse_nic_tr_html(html, keyword) if html else []

        await cache_set(ck, {"results": results, "keyword": keyword})
        return results

    async def scan_kariyer_net(self, title: str) -> list[dict[str, Any]]:
        """
        Pull active Kariyer.net job postings for a job title.

        A company hiring for a role is a textbook ``hiring_signal``
        for outreach (Phase 1-10 already scores this heavily). This
        method just feeds DiscoveryService more raw signals.
        """
        if not title or not title.strip():
            return []

        ck = cache_key("tr_kariyernet", title)
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            return cached["results"]

        url = f"https://www.kariyer.net/is-ilanlari/{urllib.parse.quote(title)}"
        html = await self._fetch_html(url, requires_js=True)
        results = self._parse_kariyer_html(html, title) if html else []

        await cache_set(ck, {"results": results, "title": title})
        return results

    # ─────────────────────────────────────────────────────
    # Aggregator helper — call them all in parallel
    # ─────────────────────────────────────────────────────

    async def discover_all(
        self,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        city: Optional[str] = None,
        title: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Convenience helper: fan out to every relevant TR source in
        parallel and return a flat, deduplicated result list.

        Used by ``DiscoveryService`` as a "TR boost" stage that runs
        alongside the regular ScrapingDog Google search.
        """
        import asyncio

        coros = []
        if company_name:
            coros.append(self.search_tobb(company_name))
            coros.append(self.scan_com_tr_domains(company_name))
        if industry and city:
            coros.append(self.search_kosgeb(industry, city))
        if city:
            coros.append(self.search_chamber(city))
        if title:
            coros.append(self.scan_kariyer_net(title))

        if not coros:
            return []

        gathered = await asyncio.gather(*coros, return_exceptions=True)
        flat: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for batch in gathered:
            if isinstance(batch, BaseException):
                logger.debug("TR source failed: %s", batch)
                continue
            for item in batch:
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    flat.append(item)
        return flat

    # ─────────────────────────────────────────────────────
    # Internal: HTTP / browser plumbing
    # ─────────────────────────────────────────────────────

    async def _fetch_html(self, url: str, requires_js: bool) -> Optional[str]:
        """
        Fetch a URL and return HTML, picking the cheapest engine that
        can handle it.

        * ``requires_js=False`` → plain ``httpx.AsyncClient`` (free).
        * ``requires_js=True``  → :class:`StealthBrowser` over IPRoyal
          residential proxy with a TR exit IP.

        Always returns ``None`` on failure (network, 4xx, 5xx, timeout).
        """
        if not requires_js:
            return await self._fetch_html_httpx(url)
        return await self._fetch_html_stealth(url)

    async def _fetch_html_httpx(self, url: str) -> Optional[str]:
        proxy = self._build_iproyal_proxy_url()
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                proxies=proxy,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/127.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
                },
            ) as http:
                resp = await http.get(url)
                if resp.status_code >= 400:
                    logger.warning("TR source %d for %s", resp.status_code, url)
                    return None
                return resp.text
        except Exception as exc:
            logger.warning("TR httpx fetch failed for %s: %s", url, exc)
            return None

    async def _fetch_html_stealth(self, url: str) -> Optional[str]:
        if not self.use_stealth:
            return await self._fetch_html_httpx(url)

        try:
            if self._stealth_cls is None:
                from app.scraping.stealth_browser import StealthBrowser
                self._stealth_cls = StealthBrowser
        except Exception as exc:
            logger.warning("StealthBrowser unavailable, falling back to httpx: %s", exc)
            return await self._fetch_html_httpx(url)

        proxy_url = self._build_iproyal_proxy_url()
        try:
            async with self._stealth_cls(proxy=proxy_url) as sb:
                await sb.navigate(url)
                return await sb.page.content()
        except Exception as exc:
            logger.warning("StealthBrowser fetch failed for %s: %s", url, exc)
            return None

    def _build_iproyal_proxy_url(self) -> Optional[str]:
        """
        Build a sticky-session IPRoyal residential proxy URL.

        Returns ``None`` when IPRoyal is not configured — the agent
        then falls back to a direct connection (CI / dev laptops).
        """
        if not (settings.IPROYAL_USERNAME and settings.IPROYAL_PASSWORD):
            return None
        session_id = random.randint(1, max(settings.IPROYAL_POOL_SIZE, 1))
        user = f"{settings.IPROYAL_USERNAME}-session-{session_id}-country-tr"
        return f"http://{user}:{settings.IPROYAL_PASSWORD}@{settings.IPROYAL_ENDPOINT}"

    # ─────────────────────────────────────────────────────
    # Internal: HTML parsers (kept simple — best-effort)
    # ─────────────────────────────────────────────────────
    # NOTE: TR public sites change their markup often. These parsers
    # are intentionally lenient and return [] when the structure
    # changes, instead of crashing the discovery pipeline. A periodic
    # job (Phase 12+) will re-validate them weekly.

    @staticmethod
    def _parse_tobb_html(html: str, query: str) -> list[dict[str, Any]]:
        """Parse TOBB member search results out of HTML."""
        return TRSourceAgent._extract_links(
            html,
            source="tobb",
            url_filter=lambda u: "uye.tobb.org.tr" in u or "tobb.org.tr/firma" in u,
            query=query,
        )

    @staticmethod
    def _parse_kosgeb_html(html: str, industry: str, city: str) -> list[dict[str, Any]]:
        return TRSourceAgent._extract_links(
            html,
            source="kosgeb",
            url_filter=lambda u: "kosgeb.gov.tr" in u,
            query=f"{industry} {city}",
        )

    @staticmethod
    def _parse_chamber_html(html: str, chamber: str, city: str) -> list[dict[str, Any]]:
        return TRSourceAgent._extract_links(
            html,
            source=f"chamber_{chamber.lower()}",
            url_filter=lambda u: any(d in u for d in ("ito.org.tr", "atonet.org.tr", "izto.org.tr")),
            query=city,
        )

    @staticmethod
    def _parse_nic_tr_html(html: str, keyword: str) -> list[dict[str, Any]]:
        return TRSourceAgent._extract_links(
            html,
            source="nic_tr",
            url_filter=lambda u: ".com.tr" in u or "nic.tr" in u,
            query=keyword,
        )

    @staticmethod
    def _parse_kariyer_html(html: str, title: str) -> list[dict[str, Any]]:
        return TRSourceAgent._extract_links(
            html,
            source="kariyer_net",
            url_filter=lambda u: "kariyer.net" in u and "/is-ilanlari/" in u,
            query=title,
        )

    @staticmethod
    def _extract_links(
        html: str,
        source: str,
        url_filter,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Tiny HTML link extractor — uses BeautifulSoup if available,
        else a regex fallback. Returns DiscoveryService-shaped dicts.
        """
        if not html:
            return []

        anchors: list[tuple[str, str]] = []
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                anchors.append((a.get_text(strip=True), a["href"]))
        except Exception:
            import re
            for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', html, re.I):
                anchors.append((match.group(2).strip(), match.group(1)))

        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for text, href in anchors:
            if not href or not url_filter(href):
                continue
            if href in seen:
                continue
            seen.add(href)
            results.append({
                "title": text or source,
                "url": href,
                "snippet": f"{source} hit for '{query}'",
                "source": source,
                "country": "TR",
                "extra": {"query": query},
            })
            if len(results) >= 25:
                break
        return results


__all__ = ["TRSourceAgent"]
