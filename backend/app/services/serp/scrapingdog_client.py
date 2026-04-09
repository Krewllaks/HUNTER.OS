"""
HUNTER.OS - ScrapingDog SERP Client (Phase 11)
================================================
Cheapest production-grade SERP API as of 2026.

Pricing
-------
* $3 per 1,000 requests
* Free tier: 1,000 requests / month
* Docs: https://www.scrapingdog.com/documentation/google

Why ScrapingDog?
----------------
DiscoveryService used to scrape Google directly with ``httpx`` +
``BeautifulSoup`` which trips Google's CAPTCHA after a few queries
and returns 5–6 leads max. ScrapingDog handles the proxy farm,
CAPTCHA solving, and result normalisation server-side, so we get
20+ clean results per query for less than $0.003 per query.

Cost guard
----------
Every search hits the Phase 11 cache layer first. Repeating the same
query within ``CACHE_TTL_DAYS`` (default 30 days) costs **zero** API
calls. Combined with the cross-product lead pool, this is what makes
the Pro plan ($49 unlimited) sustainable.

Failure mode
------------
If ScrapingDog is down, rate-limited, or the key is missing, every
public method returns ``None``. The caller (``DiscoveryService``)
treats ``None`` as "fall back to stealth Playwright Google scraping".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.core.cache import cache_get, cache_key, cache_set

logger = logging.getLogger(__name__)

_BASE_URL: str = "https://api.scrapingdog.com/google"
_DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=5.0)

# Exponential backoff for rate limit (HTTP 429): 1s, 2s, 4s, 8s
_BACKOFF_SCHEDULE: tuple[float, ...] = (1.0, 2.0, 4.0)


class ScrapingDogClient:
    """
    Async client for the ScrapingDog Google SERP endpoint.

    Usage
    -----
    >>> client = ScrapingDogClient(api_key=settings.SCRAPINGDOG_API_KEY)
    >>> results = await client.search('site:linkedin.com/in "CTO" "Istanbul"', num=20)
    >>> for r in results or []:
    ...     print(r["title"], r["url"])
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    async def search(
        self,
        query: str,
        num: int = 20,
        country: str = "tr",
    ) -> Optional[list[dict[str, Any]]]:
        """
        Run a Google search via ScrapingDog and return normalised results.

        Parameters
        ----------
        query : str
            The Google query (operators like ``site:``, ``intitle:`` are
            allowed and encouraged — that's the whole point).
        num : int, optional
            Maximum results to return. ScrapingDog caps at 100; we cap
            at 20 by default to keep cost predictable.
        country : str, optional
            Two-letter country code. Defaults to ``"tr"`` because the
            HUNTER.OS launch market is Türkiye.

        Returns
        -------
        list[dict] | None
            ``[{"title", "url", "snippet", "position"}, ...]`` on success.
            ``None`` if the API key is missing, the call fails after
            retries, or the response is empty. Callers must treat
            ``None`` as a fallback signal.
        """
        if not self.api_key:
            logger.debug("ScrapingDog disabled (no API key)")
            return None

        if not query or not query.strip():
            return None

        # Cache check — same query within TTL costs $0
        ck = cache_key("serp", query, country, str(num))
        cached = await cache_get(ck)
        if cached and isinstance(cached.get("results"), list):
            logger.info("ScrapingDog cache HIT (%d results) for %r", len(cached["results"]), query[:80])
            return cached["results"]

        params = {
            "api_key": self.api_key,
            "query": query,
            "results": min(max(num, 1), 100),
            "country": country,
            "page": 0,
        }

        raw_data: Optional[dict[str, Any]] = None

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as http:
            for attempt in range(len(_BACKOFF_SCHEDULE) + 1):
                try:
                    resp = await http.get(_BASE_URL, params=params)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    logger.warning("ScrapingDog network error (attempt %d): %s", attempt + 1, exc)
                    if attempt < len(_BACKOFF_SCHEDULE):
                        await asyncio.sleep(_BACKOFF_SCHEDULE[attempt])
                        continue
                    return None

                # 429 rate limit → exponential backoff
                if resp.status_code == 429:
                    if attempt < len(_BACKOFF_SCHEDULE):
                        sleep_for = _BACKOFF_SCHEDULE[attempt]
                        logger.warning(
                            "ScrapingDog 429 rate-limited, sleeping %.1fs (attempt %d)",
                            sleep_for, attempt + 1,
                        )
                        await asyncio.sleep(sleep_for)
                        continue
                    logger.error("ScrapingDog 429 exhausted retries")
                    return None

                # 4xx (other) → permanent fail, don't retry
                if 400 <= resp.status_code < 500:
                    logger.error(
                        "ScrapingDog %d for %r: %s",
                        resp.status_code, query[:80], resp.text[:200],
                    )
                    return None

                # 5xx → retry once with backoff
                if resp.status_code >= 500:
                    if attempt < len(_BACKOFF_SCHEDULE):
                        await asyncio.sleep(_BACKOFF_SCHEDULE[attempt])
                        continue
                    logger.error("ScrapingDog 5xx exhausted retries")
                    return None

                # 2xx success
                try:
                    raw_data = resp.json()
                except ValueError as exc:
                    logger.error("ScrapingDog returned non-JSON: %s", exc)
                    return None
                break

        if not raw_data:
            return None

        results = self._parse_results(raw_data)
        if not results:
            logger.info("ScrapingDog returned 0 organic results for %r", query[:80])
            return None

        # Cache the success — only the list of results, not the wrapping
        await cache_set(ck, {"results": results, "query": query})
        logger.info("ScrapingDog OK (%d results) for %r", len(results), query[:80])
        return results

    @staticmethod
    def _parse_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Normalise a ScrapingDog response into the dict shape that
        ``DiscoveryService._analyze_and_extract`` already understands:
        ``{"title", "url", "snippet", "position"}``.

        ScrapingDog wraps organic hits under ``organic_results`` (or
        ``organic_data`` in some plans). We accept both.
        """
        organic = raw.get("organic_results") or raw.get("organic_data") or []
        if not isinstance(organic, list):
            return []

        normalised: list[dict[str, Any]] = []
        for idx, item in enumerate(organic):
            if not isinstance(item, dict):
                continue
            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("snippet") or item.get("description") or ""
            if not url:
                continue
            normalised.append({
                "title": str(title).strip(),
                "url": str(url).strip(),
                "snippet": str(snippet).strip(),
                "position": item.get("position", idx + 1),
            })
        return normalised


__all__ = ["ScrapingDogClient"]
