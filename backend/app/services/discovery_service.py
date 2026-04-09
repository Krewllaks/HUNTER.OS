"""
HUNTER.OS - Customer Discovery Service
Autonomous pipeline: ICP → Google Dorking → httpx Search → AI Analyze → Score → Save as Leads.
Enhanced with Google Dorking, cross-product lead reuse, profile caching,
smart deduplication, and real-time progress tracking.

Search engine: httpx + BeautifulSoup (no Playwright needed → no Windows subprocess issues).
"""
import json
import logging
import asyncio
import concurrent.futures
import re
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.lead import Lead
from app.models.product import Product
from app.models.lead_product import LeadProduct
from app.services.event_bus import event_bus
# ADDED (Phase 11): cost-optimised SERP + cache + TR moat
from app.core.cache import cache_get, cache_set, cache_key
from app.services.serp.scrapingdog_client import ScrapingDogClient
from app.services.scout.tr_source_agent import TRSourceAgent

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync context safely.

    - If no event loop is running, uses asyncio.run() which on Python 3.12+
      defaults to ProactorEventLoop on Windows (subprocess-safe).
    - If called from within an existing loop (e.g. FastAPI's async handler
      dispatching to a sync background task), runs in a thread to avoid deadlock.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Inside an existing loop — run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)


# ── httpx headers — rotate user agents to avoid blocks ────────
_SEARCH_HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]

# Cache validity period
CACHE_MAX_AGE_DAYS = 30


# ── Google Dorking Templates ────────────────────────────────
# These are battle-tested search patterns that extract real leads from Google.
# Each template targets a specific type of lead source.
DORK_TEMPLATES = {
    # Find people on LinkedIn with specific titles
    "linkedin_title": 'site:linkedin.com/in "{title}" "{industry}"',
    # Find company contact/about pages
    "company_contact": '"{industry}" "{title}" "email" OR "contact" OR "@"',
    # Find people who wrote about the topic (thought leaders / potential buyers)
    "thought_leaders": '"{keyword}" "{title}" inurl:blog OR inurl:article',
    # Find companies in a specific niche using job listings
    "hiring_signal": '"{industry}" "we are hiring" OR "job opening" "{keyword}"',
    # Find directories and lists of companies
    "company_lists": '"{industry}" "top companies" OR "best companies" OR "directory" "{location}"',
    # Find decision makers via press releases or news
    "press_mentions": '"{title}" "{industry}" "announced" OR "launched" OR "partnership"',
    # Find people on Twitter/X discussing relevant topics
    "social_signal": 'site:twitter.com OR site:x.com "{keyword}" "{industry}"',
}


class DiscoveryService:
    """
    Orchestrates the full autonomous customer discovery pipeline:
    1. Use ICP profile to generate Google Dorking queries
    2. Search Google with advanced operators (site:, intitle:, inurl:, etc.)
    3. Deduplicate against existing lead pool
    4. Analyze with AI for buying signals + lead extraction
    5. Score and save as Lead records + LeadProduct junction
    """

    def __init__(self, db: Session):
        self.db = db
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction="You are ARES, an AI sales intelligence agent. Respond with valid JSON only.",
        )
        # Global semaphore: max 2 concurrent Gemini calls to avoid rate limits
        self._gemini_sem = asyncio.Semaphore(2)

    # ── SSE Event Publishing ───────────────────────────────────
    def _sse_channel(self, user_id: int, product_id: int) -> str:
        return f"hunt:{user_id}:{product_id}"

    def _publish_sse(self, user_id: int, product_id: int, event_type: str, data: dict) -> None:
        """Publish an SSE event to subscribers watching this hunt."""
        try:
            event_bus.publish(self._sse_channel(user_id, product_id), event_type, data)
        except Exception as exc:
            logger.debug("SSE publish failed (best-effort): %s", exc)

    def discover_customers(self, product: Product, user_id: int):
        """Main entry point — runs the full discovery pipeline.

        Note: asyncio.run() on Python 3.12+ uses ProactorEventLoop on Windows
        by default, so subprocess support (Playwright etc.) works out of the box.
        """
        try:
            _run_async(self._async_discover(product, user_id))
        except Exception as e:
            logger.error(f"Discovery pipeline failed: {e}")
            self._update_progress(product, phase="error", detail=str(e), error=str(e))

    # ── Progress Tracking ─────────────────────────────────────
    def _update_progress(self, product: Product, **kwargs):
        """Update hunt progress on the product record (real-time tracking)."""
        progress = product.hunt_progress or {}
        progress.update(kwargs)

        # Calculate percent based on phase
        phase = progress.get("phase", "")
        queries_total = progress.get("queries_total", 1)
        queries_done = progress.get("queries_done", 0)
        results_analyzed = progress.get("results_analyzed", 0)
        results_total = progress.get("results_total", 1)

        if phase == "generating_queries":
            progress["percent"] = 5
        elif phase == "searching":
            progress["percent"] = 5 + int((queries_done / max(queries_total, 1)) * 35)
        elif phase == "deduplicating":
            progress["percent"] = 42
        elif phase == "analyzing":
            progress["percent"] = 42 + int((results_analyzed / max(results_total, 1)) * 48)
        elif phase == "complete":
            progress["percent"] = 100
            progress["finished_at"] = datetime.now(timezone.utc).isoformat()
        elif phase == "error":
            progress["finished_at"] = datetime.now(timezone.utc).isoformat()

        product.hunt_progress = progress
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(product, "hunt_progress")
        try:
            self.db.commit()
        except Exception as exc:
            logger.warning("DB commit failed during progress update, rolling back: %s", exc)
            self.db.rollback()

    async def _async_discover(self, product: Product, user_id: int):
        """Async discovery pipeline with Google Dorking + cross-product lead reuse."""
        icp = product.icp_profile or {}
        search_strategies = product.search_queries or {}

        # Initialize progress
        self._update_progress(
            product,
            phase="generating_queries",
            percent=0,
            detail="Generating Google Dorking queries from ICP...",
            queries_total=0,
            queries_done=0,
            results_found=0,
            results_analyzed=0,
            results_total=0,
            leads_created=0,
            leads_reused=0,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=None,
            error=None,
        )

        # Step 1: Generate Google Dorking queries from ICP
        queries = await self._generate_dork_queries(product, icp, search_strategies)
        logger.info(f"Generated {len(queries)} dorking queries for: {product.name}")

        self._update_progress(
            product,
            phase="searching",
            queries_total=len(queries),
            queries_done=0,
            detail=f"Searching Google with {len(queries)} dorking queries...",
        )

        # Step 2: Execute searches with a SINGLE browser instance (efficiency)
        raw_results = await self._search_all_queries(product, queries)

        self._update_progress(
            product,
            phase="searching",
            queries_done=len(queries),
            results_found=len(raw_results),
            detail=f"Found {len(raw_results)} raw results from {len(queries)} queries",
        )
        logger.info(f"Found {len(raw_results)} raw results from search")

        # Step 3: Deduplicate by domain
        self._update_progress(product, phase="deduplicating", detail="Removing duplicates...")

        seen_domains = set()
        unique_results = []
        for result in raw_results:
            domain = self._extract_domain(result.get("url", ""))
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                unique_results.append(result)

        # Step 4: Analyze with AI — skip re-scraping if cached
        leads_created = 0
        leads_reused = 0
        analyze_targets = unique_results[:40]  # Increased from 20 for more lead coverage

        self._update_progress(
            product,
            phase="analyzing",
            results_total=len(analyze_targets),
            results_analyzed=0,
            detail=f"Analyzing {len(analyze_targets)} unique results with AI...",
        )

        for idx, result in enumerate(analyze_targets):
            try:
                domain = self._extract_domain(result.get("url", ""))

                self._update_progress(
                    product,
                    phase="analyzing",
                    results_analyzed=idx,
                    detail=f"Analyzing [{idx+1}/{len(analyze_targets)}]: {result.get('title', '')[:50]}...",
                )

                # Check if lead already exists in pool
                existing_lead = self._find_existing_lead(user_id, result, domain)

                if existing_lead:
                    linked = self._link_lead_to_product(existing_lead, product, icp)
                    if linked:
                        leads_reused += 1
                        self._update_progress(product, leads_reused=leads_reused)
                    continue

                # New lead — analyze with AI (use snippet, no extra scraping for speed)
                lead_data = await self._analyze_and_extract(result, product, icp)
                # ADDED (Phase 11): intent score gate — discard low-signal results.
                # The legacy threshold of 40 is now enforced AND the configurable
                # Phase 11 INTENT_SCORE_THRESHOLD_DISCOVERY (default 50) is checked,
                # so callers can tune cost/quality trade-offs from .env.
                discovery_threshold = max(
                    40, settings.INTENT_SCORE_THRESHOLD_DISCOVERY
                )
                score = (lead_data or {}).get("relevance_score", 0)
                if lead_data and score >= discovery_threshold:
                    self._save_lead(lead_data, user_id, product.id)
                    leads_created += 1
                    self._update_progress(product, leads_created=leads_created)
                elif lead_data:
                    logger.info(
                        f"Skipping lead creation: score={score} < "
                        f"threshold={discovery_threshold}"
                    )
            except Exception as e:
                logger.warning(f"Failed to analyze result: {e}")

        # Step 5: Update product status
        product.status = "active"
        self._update_progress(
            product,
            phase="complete",
            results_analyzed=len(analyze_targets),
            leads_created=leads_created,
            leads_reused=leads_reused,
            detail=f"Hunt complete! {leads_created} new leads, {leads_reused} reused.",
        )

        logger.info(
            f"Discovery complete for {product.name}: "
            f"{leads_created} new leads, {leads_reused} reused from pool"
        )

    # ── Google Dorking Query Generation ──────────────────────────

    async def _generate_dork_queries(self, product: Product, icp: dict, strategies: dict) -> list[str]:
        """
        Generate Google Dorking queries using two approaches:
        1. Template-based dorking (fast, reliable)
        2. AI-generated dorking (creative, diverse)
        Combine and deduplicate both.
        """
        # Extract ICP components
        industries = icp.get("industries", [])
        titles = icp.get("target_titles", [])
        pain_points = icp.get("pain_points", [])
        keywords = icp.get("keywords", [])
        company_sizes = icp.get("company_sizes", [])

        # ── 1. Template-based dorking ────────────────────
        self._current_icp = icp  # Store for geography access in template builder
        template_queries = self._build_template_dorks(industries, titles, keywords)

        # ── 2. AI-generated dorking ──────────────────────
        ai_queries = await self._generate_ai_dorks(product, icp, strategies)

        # Combine, deduplicate, limit to 15 (more queries = more leads)
        all_queries = []
        seen = set()
        for q in template_queries + ai_queries:
            q_clean = q.strip()
            q_lower = q_clean.lower()
            if q_lower not in seen and len(q_clean) > 10:
                seen.add(q_lower)
                all_queries.append(q_clean)

        # Limit to 15 queries max (increased from 8 for better coverage)
        return all_queries[:15]

    def _build_template_dorks(self, industries: list, titles: list, keywords: list) -> list[str]:
        """Build Google Dorking queries from templates + ICP data.

        Generates more queries across multiple title/industry combinations
        for better lead coverage.
        """
        queries = []

        # Filter out garbage keywords (stopwords, too short)
        _stopwords = {'we', 'sell', 'an', 'a', 'the', 'is', 'for', 'and', 'or', 'to', 'in', 'of', 'on', 'by', 'with', 'our', 'your', 'their', 'this', 'that', 'from', 'at', 'as', 'it', 'be', 'are', 'was', 'not', 'but'}
        clean_keywords = [k for k in keywords if k.lower() not in _stopwords and len(k) >= 4]

        # Use ICP geography if available
        icp = getattr(self, '_current_icp', {}) or {}
        geography = icp.get("geography", [])
        geo_str = f' "{geography[0]}"' if geography else ""

        # Use up to 3 industries and 3 titles for cross-product queries
        top_industries = industries[:3] if industries else [""]
        top_titles = titles[:3] if titles else ["CEO"]
        top_keywords = clean_keywords[:3] if clean_keywords else [top_industries[0]]

        # LinkedIn profile searches — one per title×industry combo (highest quality)
        for title in top_titles:
            for industry in top_industries[:2]:
                if title and industry:
                    queries.append(f'site:linkedin.com/in "{title}" "{industry}"{geo_str}')

        # Company contact pages with email signals
        for industry in top_industries:
            if industry:
                queries.append(f'"{industry}" "{top_titles[0]}" "email" OR "@" OR "contact"{geo_str}')

        # Thought leaders / blog authors
        for kw in top_keywords[:2]:
            if kw:
                queries.append(f'"{kw}" "{top_titles[0]}" blog OR article OR interview')

        # Hiring signal = growing company = budget exists
        for industry in top_industries[:2]:
            if industry:
                queries.append(f'"{industry}" "hiring" OR "we are looking" "{top_keywords[0] if top_keywords else industry}"')

        # Press / news mentions (active companies)
        if top_industries[0]:
            queries.append(f'"{top_titles[0]}" "{top_industries[0]}" "announced" OR "launched" OR "raised"')

        # Twitter/X thought leaders
        for title in top_titles[:2]:
            if title and top_industries[0]:
                queries.append(f'site:twitter.com OR site:x.com "{title}" "{top_industries[0]}"')

        # ── ADDED (Phase 11): aggressive extended dorks ──
        # These widen the net 10x by hitting hiring signals, funding
        # signals, tech-stack fingerprints, podcast/interview presence,
        # GitHub developer footprints, and TR-specific job boards.
        primary_industry = top_industries[0] if top_industries[0] else ""
        primary_title = top_titles[0] if top_titles else "CEO"
        primary_keyword = top_keywords[0] if top_keywords else primary_industry
        city = (icp.get("geography") or [""])[0]

        if primary_industry:
            # Hiring signal — TR + EN
            queries.append(
                f'"{primary_industry}" ("we\'re hiring" OR "join our team" OR "iş ilanı" OR "kariyer")'
            )
            # Funding signal — TR + EN
            queries.append(
                f'"{primary_industry}" ("raised" OR "series a" OR "seed round" OR "yatırım aldık")'
            )
            # Tech stack detection
            queries.append(
                f'"{primary_industry}" ("powered by shopify" OR "built with react" OR "tech stack")'
            )
            # Turkey startup directory
            if city:
                queries.append(f'{primary_industry} Turkey startup OR girişim "{city}"')

        if primary_title:
            # GitHub presence (CTO/dev detection)
            queries.append(f'site:github.com "{primary_industry}"' if primary_industry else f'site:github.com "{primary_title}"')
            # Kariyer.net job boards (TR)
            queries.append(f'site:kariyer.net "{primary_title}"')
            # Podcast / interview presence
            queries.append(
                f'"{primary_title}" "{primary_industry}" (podcast OR interview OR röportaj) site:youtube.com'
            )
            # LinkedIn people search w/ city
            if city and primary_industry:
                queries.append(
                    f'site:linkedin.com/in intitle:"{primary_title}" "{primary_industry}" "{city}"'
                )

        return queries

    async def _generate_ai_dorks(self, product: Product, icp: dict, strategies: dict) -> list[str]:
        """Use Gemini to generate advanced Google Dorking queries."""
        existing_queries = strategies.get("google_queries", []) + strategies.get("linkedin_queries", [])

        prompt = f"""You are an expert OSINT researcher. Generate 8 Google Dorking queries to find potential customers.

PRODUCT: {product.name}
DESCRIPTION: {product.description_prompt[:500]}
TARGET INDUSTRIES: {icp.get('industries', [])}
TARGET JOB TITLES: {icp.get('target_titles', [])}
PAIN POINTS: {icp.get('pain_points', [])}
KEYWORDS: {icp.get('keywords', [])}

GOOGLE DORKING RULES:
- Use "site:" to target specific platforms (linkedin.com/in, twitter.com)
- Use "intitle:" to find pages with specific title keywords
- Use "inurl:" to target specific URL patterns (contact, about, team)
- Use exact phrases with quotes: "CEO" "marketing agency"
- Use OR to combine alternatives: "CEO" OR "founder" OR "owner"
- Use "-" to exclude: -site:youtube.com -site:facebook.com
- Target REAL PEOPLE, not generic pages
- Queries should find decision-makers who NEED this product

BAD QUERIES (DO NOT GENERATE THESE):
- "{product.name} users" (too generic)
- "{product.description_prompt[:50]}" (just the product name)
- Generic queries without operators

GOOD QUERIES (LIKE THESE):
- site:linkedin.com/in "operations manager" "manufacturing" "safety"
- "head of safety" OR "safety director" "company" "@" -site:linkedin.com
- intitle:"occupational health" "software" "contact" inurl:about

Return JSON: {{"queries": ["query1", "query2", ...]}}"""

        result = await self._gemini_call(prompt, temperature=0.6, max_retries=2)
        if result:
            return result.get("queries", [])
        return []

    # ── Google Search (httpx — no browser needed) ────────────────────

    async def _search_all_queries(self, product: Product, queries: list[str]) -> list[dict]:
        """
        Execute SERP queries with cost-optimised waterfall (Phase 11):

            cache → ScrapingDog ($3 / 1000) → DDG SDK → httpx scraping chain

        Each query result is cached for ``CACHE_TTL_DAYS`` so the same
        dork against the same product never costs more than once. Order
        matters: ScrapingDog gives the highest signal density per dollar
        and is tried first whenever an API key is configured. Falls
        through gracefully when ScrapingDog is unavailable / disabled.
        """
        all_results: list[dict] = []
        scrapingdog = (
            ScrapingDogClient(api_key=settings.SCRAPINGDOG_API_KEY)
            if settings.SCRAPINGDOG_API_KEY else None
        )

        for i, query in enumerate(queries):
            self._update_progress(
                product,
                phase="searching",
                queries_done=i,
                detail=f"Dorking [{i+1}/{len(queries)}]: {query[:55]}...",
            )

            # ── 1. Cache check (Phase 11) ───────────────────
            ck = cache_key("serp", query)
            cached = await cache_get(ck)
            if cached and isinstance(cached, list):
                all_results.extend(cached)
                logger.info(f"Query [{i+1}/{len(queries)}] cache hit: {query[:50]}")
                continue

            results: list[dict] = []

            # ── 2. ScrapingDog (Phase 11, cheapest paid SERP) ──
            if scrapingdog:
                try:
                    sd_results = await scrapingdog.search(query=query, num=20, country="tr")
                    if sd_results:
                        results = sd_results
                except Exception as exc:
                    logger.debug(f"ScrapingDog failed for '{query[:40]}': {exc}")

            # ── 3. Fallback: existing DDG SDK ───────────────
            if not results:
                results = await self._search_ddg_sdk(query)

            # ── 4. Fallback: httpx scraping chain (last resort) ──
            if not results:
                async with httpx.AsyncClient(
                    timeout=15.0, follow_redirects=True, verify=False,
                ) as client:
                    results = await self._search_duckduckgo(client, query)
                    if not results:
                        results = await self._search_google_httpx(client, query)
                    if not results:
                        results = await self._search_bing(client, query)

            # ── 5. Cache & collect ─────────────────────────
            if results:
                try:
                    await cache_set(ck, results)
                except Exception as exc:
                    logger.debug(f"SERP cache_set failed (non-fatal): {exc}")
                all_results.extend(results)

            logger.info(f"Query [{i+1}/{len(queries)}] returned {len(results)} results: {query[:50]}")

            # Human-like delay between searches (1-3 seconds) — only when
            # we actually hit the network. Cache hits skip the delay.
            if i < len(queries) - 1 and results:
                await asyncio.sleep(random.uniform(1.0, 3.0))

        return all_results

    async def _search_ddg_sdk(self, query: str) -> list[dict]:
        """Search using duckduckgo-search Python SDK (most reliable, no scraping).

        DDG doesn't support advanced operators like site: well,
        so we strip them and use plain language queries.
        """
        try:
            from duckduckgo_search import DDGS
            loop = asyncio.get_running_loop()

            # DDG doesn't handle site: operator — convert to natural query
            clean_query = query
            if "site:" in clean_query:
                # site:linkedin.com/in "CEO" "SaaS" → linkedin "CEO" "SaaS"
                clean_query = re.sub(r'site:\S+', 'linkedin', clean_query)

            def _sync_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(clean_query, region="us-en", max_results=25))

            raw = await loop.run_in_executor(None, _sync_search)

            results = []
            for item in raw:
                url = item.get("href", "")
                title = item.get("title", "")
                snippet = item.get("body", "")
                if url and title:
                    results.append({"url": url, "title": title, "snippet": snippet})

            logger.info(f"DDG SDK returned {len(results)} results for: {clean_query[:50]}")
            return results
        except Exception as e:
            logger.warning(f"DDG SDK failed: {e}")
            return []

    async def _search_google_httpx(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search Google via httpx + BeautifulSoup HTML parsing."""
        encoded_query = quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}&num=20&hl=en"
        headers = random.choice(_SEARCH_HEADERS_POOL)

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Google returned {resp.status_code} for: {query[:40]}")
                return []

            html = resp.text
            # CAPTCHA detection
            if "unusual traffic" in html.lower() or "captcha" in html.lower():
                logger.warning(f"Google CAPTCHA for: {query[:40]}, switching to fallback")
                return []

            return self._parse_google_html(html)
        except Exception as e:
            logger.error(f"Google httpx search failed: {e}")
            return []

    def _parse_google_html(self, html: str) -> list[dict]:
        """Parse Google search results from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Strategy 1: Standard result blocks with class 'g'
        for item in soup.select(".g"):
            link = item.select_one("a[href]")
            title_el = item.select_one("h3")
            snippet_el = (
                item.select_one(".VwiC3b")
                or item.select_one("[data-snf]")
                or item.select_one(".IsZvec")
                or item.select_one("span.st")
            )
            if link and title_el:
                href = link.get("href", "")
                if href and "google.com" not in href and not href.startswith("javascript:"):
                    results.append({
                        "url": href,
                        "title": title_el.get_text(strip=True),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })

        # Strategy 2: data-header-feature links
        if not results:
            for a in soup.select("a[href]"):
                h3 = a.select_one("h3")
                if h3:
                    href = a.get("href", "")
                    if href and "google.com" not in href:
                        results.append({
                            "url": href,
                            "title": h3.get_text(strip=True),
                            "snippet": "",
                        })

        # Strategy 3: Parse /url?q= redirect links (Google sometimes wraps URLs)
        if not results:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/url?q="):
                    actual_url = href.split("/url?q=")[1].split("&")[0]
                    title_text = a.get_text(strip=True)
                    if actual_url and "google.com" not in actual_url and len(title_text) > 5:
                        results.append({
                            "url": actual_url,
                            "title": title_text,
                            "snippet": "",
                        })

        return results[:20]

    async def _search_duckduckgo(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Fallback: Search DuckDuckGo HTML (no API key needed, no CAPTCHA)."""
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        headers = random.choice(_SEARCH_HEADERS_POOL)

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for item in soup.select(".result"):
                link = item.select_one("a.result__a")
                snippet_el = item.select_one(".result__snippet")
                if link:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    # DDG wraps URLs via redirect
                    if "duckduckgo.com" in href:
                        # Extract actual URL from DDG redirect
                        from urllib.parse import unquote
                        match = re.search(r'uddg=([^&]+)', href)
                        if match:
                            href = unquote(match.group(1))
                    if href and title:
                        results.append({
                            "url": href,
                            "title": title,
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })

            logger.info(f"DuckDuckGo returned {len(results)} results")
            return results[:20]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    async def _search_bing(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Fallback: Search Bing (no API key needed)."""
        encoded_query = quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded_query}&count=20"
        headers = random.choice(_SEARCH_HEADERS_POOL)

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for item in soup.select(".b_algo"):
                link = item.select_one("h2 a")
                snippet_el = item.select_one(".b_caption p")
                if link:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    if href and title:
                        results.append({
                            "url": href,
                            "title": title,
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })

            logger.info(f"Bing returned {len(results)} results")
            return results[:20]
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []

    # ── Gemini Rate Limit Handling ─────────────────────────────────

    async def _gemini_call(self, prompt: str, temperature: float = 0.2, max_retries: int = 5) -> Optional[dict]:
        """
        Call Gemini with exponential backoff for rate limits.
        Returns parsed JSON or None on failure.
        """
        for attempt in range(max_retries):
            try:
                async with self._gemini_sem:
                    response = await self.model.generate_content_async(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            response_mime_type="application/json",
                        ),
                    )
                return json.loads(response.text.strip())
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower() or "resource_exhausted" in error_str.lower():
                    # Rate limited — longer exponential backoff
                    wait = min((2 ** attempt) * 10, 120)  # 10s, 20s, 40s, 80s, 120s max
                    logger.warning(f"Gemini rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Gemini call failed: {e}")
                    return None
        logger.error("Gemini rate limit exceeded after all retries")
        return None

    # ── Analysis & Extraction ─────────────────────────────────────

    async def _analyze_and_extract(self, search_result: dict, product: Product, icp: dict) -> Optional[dict]:
        """
        Analyze a search result and extract lead data.
        Strategy: Try AI first → fallback to regex extraction if rate limited.
        """
        url = search_result.get("url", "")
        title = search_result.get("title", "")
        snippet = search_result.get("snippet", "")

        is_linkedin = "linkedin.com/in/" in url

        # For LinkedIn profiles, try regex extraction first (fast, no API needed)
        if is_linkedin:
            regex_result = self._extract_linkedin_lead(url, title, snippet, product, icp)
            if regex_result:
                # Optionally enhance with AI if available
                ai_result = await self._ai_analyze(url, title, snippet, "", product, icp, is_linkedin=True)
                if ai_result:
                    # Merge: AI enriches regex base
                    regex_result.update({k: v for k, v in ai_result.items() if v and v != "null"})
                return regex_result

        # For non-LinkedIn, try regex extraction from title/snippet
        regex_result = self._extract_generic_lead(url, title, snippet, product, icp)

        # Try AI analysis (with rate limiting)
        page_content = snippet
        ai_result = await self._ai_analyze(url, title, snippet, page_content, product, icp, is_linkedin=False)

        if ai_result:
            return ai_result

        # Fallback: return regex result if AI failed (rate limit, etc.)
        return regex_result

    def _extract_linkedin_lead(self, url: str, title: str, snippet: str, product: Product, icp: dict) -> Optional[dict]:
        """
        Extract lead info from LinkedIn URL and title WITHOUT AI.
        LinkedIn URLs: linkedin.com/in/first-last-123abc
        LinkedIn titles: "First Last - Title at Company | LinkedIn"
        """
        try:
            # Extract name from URL slug
            slug_match = re.search(r'linkedin\.com/in/([a-zA-Z\-]+)', url)
            if not slug_match:
                return None

            slug = slug_match.group(1)
            # Remove trailing hash codes: "john-doe-1a2b3c" → "john-doe"
            slug_clean = re.sub(r'-[a-f0-9]{4,}$', '', slug)
            name_parts = [p.capitalize() for p in slug_clean.split('-') if len(p) > 1]

            if len(name_parts) < 2:
                return None

            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])

            # Extract title and company from LinkedIn title string
            # Pattern: "First Last - Title at Company | LinkedIn"
            job_title = None
            company = None
            title_match = re.search(r'-\s*(.+?)\s*(?:at|@|-)\s*(.+?)(?:\s*\||\s*[-–]|\s*LinkedIn)', title)
            if title_match:
                job_title = title_match.group(1).strip()
                company = title_match.group(2).strip()
            else:
                # Simpler pattern: "First Last | LinkedIn"
                parts = title.split(' - ')
                if len(parts) >= 2:
                    job_title = parts[1].split('|')[0].strip() if '|' in parts[1] else parts[1].strip()

            # Extract domain
            domain = None
            if company:
                # Guess domain from company name
                company_slug = re.sub(r'[^a-z0-9]', '', company.lower())
                if company_slug:
                    domain = f"{company_slug}.com"

            # Check if matches ICP (basic keyword matching)
            target_titles = [t.lower() for t in icp.get("target_titles", [])]
            target_industries = [i.lower() for i in icp.get("industries", [])]

            relevance_score = 55  # Base score for LinkedIn profile
            combined_text = f"{title} {snippet} {job_title or ''}".lower()

            # Boost for matching titles
            for t in target_titles:
                if t.lower() in combined_text:
                    relevance_score += 15
                    break

            # Boost for matching industries
            for ind in target_industries:
                if ind.lower() in combined_text:
                    relevance_score += 10
                    break

            if relevance_score < 50:
                return None

            return {
                "is_relevant": True,
                "relevance_score": min(relevance_score, 95),
                "reasoning": f"LinkedIn profile: {first_name} {last_name}, {job_title or 'unknown title'} at {company or 'unknown company'}",
                "first_name": first_name,
                "last_name": last_name,
                "email": None,
                "company_name": company,
                "company_domain": domain,
                "title": job_title,
                "industry": icp.get("industries", [""])[0] if icp.get("industries") else None,
                "linkedin_url": url,
                "pain_points_detected": [],
                "buying_signals": ["LinkedIn profile found via targeted search"],
                "content_summary": snippet[:200] if snippet else title,
            }
        except Exception as e:
            logger.debug(f"LinkedIn regex extraction failed: {e}")
            return None

    @staticmethod
    def _is_junk_email(email: str) -> bool:
        """Filter out fake/notification/system emails that are never real leads."""
        if not email:
            return True
        email_lower = email.lower()
        # Junk patterns: notification addresses, noreply, system mails
        junk_patterns = [
            'notification', 'noreply', 'no-reply', 'donotreply', 'do-not-reply',
            'mailer-daemon', 'postmaster', 'support@', 'info@', 'admin@',
            'newsletter', 'unsubscribe', 'feedback@', 'abuse@', 'security@',
            'alerts@', 'updates@', 'hello@', 'contact@', 'team@', 'help@',
        ]
        junk_domains = [
            'facebookmail.com', 'facebook.com', 'google.com', 'youtube.com',
            'twitter.com', 'x.com', 'instagram.com', 'tiktok.com',
            'linkedin.com', 'github.com', 'reddit.com', 'medium.com',
            'example.com', 'test.com', 'localhost', 'mailinator.com',
            'tempmail.com', 'guerrillamail.com', 'yopmail.com',
            'wikipedia.org', 'amazon.com', 'apple.com', 'microsoft.com',
        ]
        for p in junk_patterns:
            if p in email_lower:
                return True
        domain_part = email_lower.split('@')[-1] if '@' in email_lower else ''
        for d in junk_domains:
            if domain_part == d or domain_part.endswith('.' + d):
                return True
        # Random-looking local parts (e.g. notification+kjdmhjhjhpmd)
        local = email_lower.split('@')[0]
        if '+' in local and len(local.split('+')[-1]) > 6:
            return True
        return False

    def _extract_generic_lead(self, url: str, title: str, snippet: str, product: Product, icp: dict) -> Optional[dict]:
        """
        Extract basic lead info from non-LinkedIn search results WITHOUT AI.
        Looks for emails, names, company info in title and snippet.
        """
        try:
            combined_text = f"{title} {snippet}"

            # Extract email and validate
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', combined_text)
            email = email_match.group(0) if email_match else None
            if email and self._is_junk_email(email):
                email = None  # Discard junk emails

            # Extract domain from URL
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")

            # Skip generic/irrelevant domains
            skip_patterns = {
                # Lead gen / directory tools
                'amazon', 'scribd', 'apollo', 'rocketreach', 'ceoemail',
                'cognism', 'prospeo', 'listkit', 'coldlytics', 'tapclicks',
                'amplemarket', 'kariyer.net', 'facebook.com', 'facebookmail.com',
                # News & media sites (not decision-maker profiles)
                'techcrunch', 'businesswire', 'reuters', 'bloomberg', 'forbes',
                'wsj.com', 'nytimes', 'theverge', 'wired.com', 'venturebeat',
                'hackernews', 'ycombinator', 'producthunt', 'medium.com',
                'substack.com', 'reddit.com', 'twitter.com', 'x.com',
                'youtube.com', 'instagram.com', 'tiktok.com',
                # Generic/aggregator sites
                'wikipedia', 'crunchbase', 'glassdoor', 'indeed.com', 'ziprecruiter',
                'angellist', 'pitchbook', 'owler', 'dnb.com', 'zoominfo',
                'tradingview', 'zhihu', 'podcasts', 'topstartups',
                'explodingtopics', 'fintechfutures', 'startuplaunchday', 'upcarta',
            }
            if any(s in domain for s in skip_patterns):
                return None

            # Try to extract a person name from title (simple heuristic)
            first_name = None
            last_name = None

            # Check ICP relevance (keyword matching)
            target_titles = [t.lower() for t in icp.get("target_titles", [])]
            target_industries = [i.lower() for i in icp.get("industries", [])]
            keywords = [k.lower() for k in icp.get("keywords", [])]

            text_lower = combined_text.lower()
            relevance_score = 40  # Base

            for t in target_titles:
                if t in text_lower:
                    relevance_score += 15
                    break
            for ind in target_industries:
                if ind in text_lower:
                    relevance_score += 10
                    break
            for kw in keywords:
                if kw in text_lower:
                    relevance_score += 5
                    break
            if email:
                relevance_score += 10

            if relevance_score < 50:
                return None

            return {
                "is_relevant": True,
                "relevance_score": min(relevance_score, 90),
                "reasoning": f"Found via search: {title[:60]}",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company_name": domain.split('.')[0].capitalize() if domain else None,
                "company_domain": domain,
                "title": None,
                "industry": icp.get("industries", [""])[0] if icp.get("industries") else None,
                "linkedin_url": None,
                "pain_points_detected": [],
                "buying_signals": [],
                "content_summary": snippet[:200] if snippet else title,
            }
        except Exception as exc:
            logger.debug("Fallback lead extraction failed for %s: %s", url, exc)
            return None

    async def _ai_analyze(self, url: str, title: str, snippet: str, page_content: str,
                          product: Product, icp: dict, is_linkedin: bool = False) -> Optional[dict]:
        """Call Gemini AI to analyze a search result (with rate limit handling)."""
        prompt = f"""Analyze this search result and extract lead information for selling our product.

PRODUCT: {product.name}
PRODUCT DESCRIPTION: {product.description_prompt[:300]}
TARGET ICP: Industries={icp.get('industries')}, Titles={icp.get('target_titles')}, Pain Points={icp.get('pain_points')}

SEARCH RESULT:
URL: {url}
Title: {title}
Content: {(page_content or snippet)[:2000]}

{"This is a LinkedIn profile. Extract the person's name from the URL/title." if is_linkedin else ""}

Extract lead information and score relevance. Respond with JSON:
{{
    "is_relevant": true/false,
    "relevance_score": 0-100,
    "reasoning": "Why this is/isn't a good lead",
    "first_name": "extracted first name or null",
    "last_name": "extracted last name or null",
    "email": "extracted email or null",
    "company_name": "extracted company or null",
    "company_domain": "extracted domain from URL",
    "title": "their job title or null",
    "industry": "their industry",
    "linkedin_url": "{url if is_linkedin else 'null'}",
    "pain_points_detected": [],
    "buying_signals": [],
    "content_summary": "Brief summary"
}}

Rules:
- Only is_relevant=true for ACTUAL potential customers
- Score 70+ for strong matches, 50-69 for moderate"""

        result = await self._gemini_call(prompt, temperature=0.2, max_retries=2)

        if result and result.get("is_relevant"):
            return result
        return None

    # ── Lead Pool & Reuse ─────────────────────────────────────────

    def _find_existing_lead(self, user_id: int, result: dict, domain: Optional[str]) -> Optional[Lead]:
        """Check if a lead already exists by email, LinkedIn URL, or company domain."""
        filters = [Lead.user_id == user_id]
        conditions = []
        url = result.get("url", "")

        if "linkedin.com/in/" in url:
            conditions.append(Lead.linkedin_url == url)
        if domain:
            conditions.append(Lead.company_domain == domain)

        if not conditions:
            return None

        return (
            self.db.query(Lead)
            .filter(*filters)
            .filter(or_(*conditions))
            .first()
        )

    def _link_lead_to_product(self, lead: Lead, product: Product, icp: dict) -> bool:
        """Link an existing lead to a new product via LeadProduct junction."""
        existing_link = (
            self.db.query(LeadProduct)
            .filter(LeadProduct.lead_id == lead.id, LeadProduct.product_id == product.id)
            .first()
        )
        if existing_link:
            return False

        recent_links = (
            self.db.query(LeadProduct)
            .filter(
                LeadProduct.lead_id == lead.id,
                LeadProduct.last_contacted_at >= datetime.now(timezone.utc) - timedelta(days=14),
            )
            .count()
        )
        if recent_links >= 2:
            return False

        if lead.do_not_contact or lead.is_blacklisted:
            return False

        link = LeadProduct(
            lead_id=lead.id,
            product_id=product.id,
            status="new",
            fit_score=lead.icp_match_score or 0.0,
        )
        self.db.add(link)
        self.db.commit()
        logger.info(f"Reused lead {lead.id} ({lead.company_name}) for product {product.name}")
        return True

    def _is_cache_stale(self, lead: Lead) -> bool:
        """Check if lead's profile cache is too old."""
        if not lead.profile_data_cached_at:
            return True
        age = datetime.now(timezone.utc) - lead.profile_data_cached_at.replace(tzinfo=timezone.utc)
        return age.days > CACHE_MAX_AGE_DAYS

    # ── Cross-Product Matching ─────────────────────────────────

    def match_existing_leads(self, product: Product, user_id: int) -> list[dict]:
        """
        Cross-product matching: find existing leads that fit a new product's ICP.
        """
        icp = product.icp_profile or {}

        existing_lead_ids = (
            self.db.query(LeadProduct.lead_id)
            .filter(LeadProduct.product_id == product.id)
            .all()
        )
        excluded_ids = {row[0] for row in existing_lead_ids}

        leads = (
            self.db.query(Lead)
            .filter(
                Lead.user_id == user_id,
                Lead.is_blacklisted == False,
                Lead.do_not_contact == False,
            )
            .all()
        )

        candidates = [l for l in leads if l.id not in excluded_ids]
        if not candidates:
            return []

        matched = _run_async(
            self._batch_score_leads(candidates, product, icp)
        )

        created = 0
        for match in matched:
            if match["fit_score"] >= 60:
                lead = self.db.query(Lead).get(match["lead_id"])
                if lead and not lead.do_not_contact and not lead.is_blacklisted:
                    link = LeadProduct(
                        lead_id=match["lead_id"],
                        product_id=product.id,
                        status="new",
                        fit_score=match["fit_score"],
                    )
                    self.db.add(link)
                    created += 1

        self.db.commit()
        logger.info(f"Cross-product matching: {created} leads matched for {product.name}")
        return [m for m in matched if m["fit_score"] >= 60]

    async def _batch_score_leads(self, leads: list[Lead], product: Product, icp: dict) -> list[dict]:
        """Score a batch of leads against a product's ICP using Gemini."""
        results = []
        for i in range(0, len(leads), 10):
            batch = leads[i:i + 10]
            lead_summaries = []
            for lead in batch:
                summary = {
                    "id": lead.id,
                    "name": f"{lead.first_name} {lead.last_name}",
                    "company": lead.company_name,
                    "industry": lead.industry,
                    "title": lead.title,
                    "domain": lead.company_domain,
                }
                if lead.profile_cache:
                    summary["profile"] = str(lead.profile_cache)[:500]
                lead_summaries.append(summary)

            prompt = f"""Score these existing leads for fit with a new product.

PRODUCT: {product.name}
DESCRIPTION: {product.description_prompt[:500]}
TARGET ICP:
- Industries: {icp.get('industries', [])}
- Titles: {icp.get('target_titles', [])}
- Company Sizes: {icp.get('company_sizes', [])}
- Pain Points: {icp.get('pain_points', [])}

LEADS TO SCORE:
{json.dumps(lead_summaries, ensure_ascii=False, indent=2)}

For each lead, return a fit_score (0-100) and brief reasoning.
Return JSON: {{"scores": [{{"lead_id": 1, "fit_score": 75, "reason": "..."}}]}}"""

            try:
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                data = json.loads(response.text.strip())
                results.extend(data.get("scores", []))
            except Exception as e:
                logger.error(f"Batch scoring failed: {e}")

        return results

    # ── Lead Saving ──────────────────────────────────────────────

    def _save_lead(self, lead_data: dict, user_id: int, product_id: int):
        """Save extracted lead data to database with LeadProduct junction."""
        # Filter junk emails before saving
        if lead_data.get("email") and self._is_junk_email(lead_data["email"]):
            lead_data["email"] = None

        # Triple dedup: email + linkedin_url + company_domain
        conditions = []
        if lead_data.get("email"):
            conditions.append(Lead.email == lead_data["email"])
        if lead_data.get("linkedin_url"):
            conditions.append(Lead.linkedin_url == lead_data["linkedin_url"])
        if lead_data.get("company_domain"):
            conditions.append(Lead.company_domain == lead_data["company_domain"])

        if conditions:
            existing = (
                self.db.query(Lead)
                .filter(Lead.user_id == user_id)
                .filter(or_(*conditions))
                .first()
            )
            if existing:
                self._link_lead_to_product_simple(existing.id, product_id, lead_data.get("relevance_score", 0))
                return

        lead = Lead(
            user_id=user_id,
            first_name=lead_data.get("first_name") or "Unknown",
            last_name=lead_data.get("last_name") or "",
            email=lead_data.get("email"),
            linkedin_url=lead_data.get("linkedin_url"),
            company_name=lead_data.get("company_name"),
            company_domain=lead_data.get("company_domain"),
            industry=lead_data.get("industry"),
            title=lead_data.get("title"),
            intent_score=lead_data.get("relevance_score", 0),
            status="researched",
            source=f"discovery_product_{product_id}",
            content_intent=lead_data.get("content_summary", ""),
            social_engagement=lead_data.get("buying_signals", []),
            notes=lead_data.get("reasoning"),
            profile_cache={
                "pain_points": lead_data.get("pain_points_detected", []),
                "buying_signals": lead_data.get("buying_signals", []),
                "content_summary": lead_data.get("content_summary", ""),
            },
            profile_data_cached_at=datetime.now(timezone.utc),
        )
        self.db.add(lead)
        self.db.flush()

        self._link_lead_to_product_simple(lead.id, product_id, lead_data.get("relevance_score", 0))
        self.db.commit()

    def _link_lead_to_product_simple(self, lead_id: int, product_id: int, fit_score: float = 0):
        """Create LeadProduct link if not exists."""
        existing = (
            self.db.query(LeadProduct)
            .filter(LeadProduct.lead_id == lead_id, LeadProduct.product_id == product_id)
            .first()
        )
        if not existing:
            link = LeadProduct(
                lead_id=lead_id,
                product_id=product_id,
                status="new",
                fit_score=fit_score,
            )
            self.db.add(link)

    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL, skip generic platforms."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            skip_domains = {
                "google.com", "youtube.com", "facebook.com", "twitter.com",
                "wikipedia.org", "reddit.com", "github.com", "instagram.com",
                "tiktok.com", "pinterest.com", "medium.com", "quora.com",
            }
            # Keep linkedin.com — individual profiles are valid leads
            if domain in skip_domains:
                return None
            return domain
        except Exception as exc:
            logger.debug("Domain extraction failed for %s: %s", url, exc)
            return None
