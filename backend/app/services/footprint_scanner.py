"""
HUNTER.OS - Digital Footprint Scanner
Sherlock-inspired social profile discovery adapted for sales intelligence.

Scans 50 sales-relevant platforms to discover a lead's digital presence.
Uses async HTTP with concurrency limiting and proxy rotation.
"""
import asyncio
import json
import re
import time
import logging
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

import aiohttp

from app.core.config import settings
# ADDED (Phase 11): cache + Phase 11 client imports
from app.core.cache import cache_get, cache_set, cache_key

logger = logging.getLogger(__name__)

# Load site definitions
_SITES_PATH = Path(__file__).parent.parent / "data" / "sites.json"
_sites_cache: dict | None = None


def _load_sites() -> dict:
    global _sites_cache
    if _sites_cache is None:
        with open(_SITES_PATH, "r", encoding="utf-8") as f:
            _sites_cache = json.load(f)
    return _sites_cache


@dataclass
class SiteResult:
    """Result of checking a single site."""
    platform: str
    url: str
    username: str
    found: bool
    category: str = "unknown"
    sales_relevance: float = 0.5
    response_time_ms: float = 0.0
    error: str | None = None


class DigitalFootprintScanner:
    """
    Async scanner that checks username existence across 50+ platforms.

    Uses three detection methods (matching Sherlock):
    - status_code: HTTP 200 = found, 404 = not found
    - message: Search response body for error message string
    - response_url: Follow redirects, compare final URL
    """

    def __init__(
        self,
        concurrency: int = 20,
        timeout_seconds: int = 10,
        proxy_pool: list[str] | None = None,
    ):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.proxy_pool = proxy_pool or settings.PROXY_POOL or []
        self._semaphore = asyncio.Semaphore(concurrency)

    def extract_usernames(self, lead) -> list[str]:
        """Extract candidate usernames from lead data.

        Phase 11: expanded from 4 → 12+ candidate patterns. Includes
        first/last variations, dotted/dashed/underscored forms, single
        initial forms, role-based aliases (info@, contact@, sales@,
        careers@), Türkçe character normalisation (ç→c, ğ→g, ı→i,
        ö→o, ş→s, ü→u), and digit suffixes (+01..+99 are seeded with
        a couple of common values to avoid combinatorial explosion).

        Returns
        -------
        list[str]
            Deduplicated lowercase candidates, between 12 and 20 items
            when sufficient input is available, otherwise as many as
            can be derived. Never raises.
        """
        usernames: set[str] = set()

        def _norm_tr(s: str) -> str:
            """Normalise Türkçe characters → ASCII."""
            return (
                s.replace("ç", "c").replace("Ç", "c")
                 .replace("ğ", "g").replace("Ğ", "g")
                 .replace("ı", "i").replace("İ", "i")
                 .replace("ö", "o").replace("Ö", "o")
                 .replace("ş", "s").replace("Ş", "s")
                 .replace("ü", "u").replace("Ü", "u")
            )

        # ── 1. From email prefix ─────────────────────────
        email_val = getattr(lead, "email", None)
        if isinstance(email_val, str) and email_val:
            prefix = email_val.split("@")[0].lower()
            usernames.add(prefix)
            clean = re.sub(r"[._\-+]", "", prefix)
            if clean:
                usernames.add(clean)
            usernames.add(re.sub(r"[_\-+]", ".", prefix))
            usernames.add(re.sub(r"[._+]", "-", prefix))
            # Email prefix split on dot — first segment is often the first name
            for piece in re.split(r"[._\-+]", prefix):
                if 2 <= len(piece) <= 30:
                    usernames.add(piece)

        # ── 2. From LinkedIn URL slug ────────────────────
        linkedin_val = getattr(lead, "linkedin_url", None)
        if isinstance(linkedin_val, str) and linkedin_val:
            m = re.search(r"linkedin\.com/in/([^/?]+)", linkedin_val)
            if m:
                slug = m.group(1).lower()
                clean_slug = re.sub(r"-[a-f0-9]{4,}$", "", slug)
                usernames.add(clean_slug)
                usernames.add(clean_slug.replace("-", ""))
                usernames.add(clean_slug.replace("-", "."))

        # ── 3. From first / last name ────────────────────
        first_attr = getattr(lead, "first_name", None)
        last_attr = getattr(lead, "last_name", None)
        first_raw = (first_attr if isinstance(first_attr, str) else "").strip().lower()
        last_raw = (last_attr if isinstance(last_attr, str) else "").strip().lower()
        if first_raw == "unknown":
            first_raw = ""

        # Apply both raw and TR-normalised forms so Sherlock checks
        # pass even when sites strip non-ASCII.
        for first, last in {(first_raw, last_raw), (_norm_tr(first_raw), _norm_tr(last_raw))}:
            if not first or not last:
                continue
            f, l = first[0], last[0]

            # 12 baseline patterns from the spec
            usernames.update({
                f"{first}.{last}",   # 1. ahmet.yilmaz
                f"{first}_{last}",   # 2. ahmet_yilmaz
                f"{first}-{last}",   # 3. ahmet-yilmaz
                f"{first}{last}",    # 4. ahmetyilmaz
                f"{f}{last}",        # 5. ayilmaz
                f"{last}.{first}",   # 6. yilmaz.ahmet
                f"{last}{first}",    # 7. yilmazahmet
                f"{first}.{l}",      # 8. ahmet.y
                f"{f}.{last}",       # 9. a.yilmaz
                f"{first}{l}",       # 10. ahmety
                f"{last}{f}",        # 11. yilmaza
                first,               # 12. ahmet
                last,                # 13. yilmaz
            })
            # Numeric variant — common picks (avoid 99x explosion)
            for n in ("01", "1", "99"):
                usernames.add(f"{first}{last}{n}")

        # Single name fallback
        if first_raw and not last_raw:
            usernames.add(first_raw)
        if last_raw and not first_raw:
            usernames.add(last_raw)

        # ── 4. Company / role-based aliases ──────────────
        domain_attr = getattr(lead, "company_domain", None)
        domain = domain_attr if isinstance(domain_attr, str) else ""
        if domain:
            slug = re.sub(r"[^a-z0-9\-]", "", domain.lower().replace("www.", "").split(".")[0])
            if len(slug) >= 3:
                usernames.add(slug)
            for role in ("info", "contact", "sales", "careers", "hello", "team"):
                # role-based aliases are kept as bare usernames; full
                # email construction is the email-finder's job
                usernames.add(role)

        # Last resort: company name slug
        if not (first_raw or last_raw or domain):
            company_attr = getattr(lead, "company_name", None)
            company = (company_attr if isinstance(company_attr, str) else "").lower()
            if company and company not in ("unknown", ""):
                slug = re.sub(r"[^a-z0-9]", "", _norm_tr(company))[:30]
                if len(slug) >= 3:
                    usernames.add(slug)

        # ── 5. Final dedup + length filter + cap at 20 ───
        cleaned = [u for u in usernames if u and 2 <= len(u) <= 40]
        # Deterministic ordering for cache stability
        cleaned.sort()
        return cleaned[:20]

    async def scan_username(
        self,
        username: str,
        site_filter: list[str] | None = None,
    ) -> list[SiteResult]:
        """Scan a single username across all configured platforms."""
        sites = _load_sites()

        # Filter sites if requested
        if site_filter:
            filter_set = {s.lower() for s in site_filter}
            sites = {k: v for k, v in sites.items() if k.lower() in filter_set}

        connector = aiohttp.TCPConnector(
            limit=self.concurrency,
            ttl_dns_cache=300,
            ssl=False,  # Skip SSL verification for speed
        )

        results = []
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        ) as session:
            tasks = [
                self._check_site(session, site_name, site_config, username)
                for site_name, site_config in sites.items()
            ]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in raw_results:
                if isinstance(r, SiteResult):
                    results.append(r)
                elif isinstance(r, Exception):
                    logger.debug("Site check exception: %s", r)

        return results

    async def scan_lead(self, lead, custom_usernames: list[str] | None = None) -> dict:
        """Scan all candidate usernames for a lead, return aggregated results.

        Phase 11: cached for ``CACHE_TTL_DAYS`` (default 30 days). The
        cache key is derived from the lead's email / linkedin URL /
        full name / id, in that priority order. Re-scanning the same
        lead within the TTL window costs zero HTTP requests.
        """
        # ADDED (Phase 11): cache check at the very top
        ck_identifier = (
            getattr(lead, "email", None)
            or getattr(lead, "linkedin_url", None)
            or getattr(lead, "full_name", None)
            or " ".join(filter(None, [getattr(lead, "first_name", None), getattr(lead, "last_name", None)]))
            or str(getattr(lead, "id", "") or "")
        )
        ck = cache_key("footprint", ck_identifier or "anon")
        cached = await cache_get(ck)
        if cached:
            logger.info("Footprint cache hit for lead %s", getattr(lead, "id", "?"))
            return cached

        start_time = time.monotonic()

        usernames = self.extract_usernames(lead)
        if custom_usernames:
            usernames.extend(custom_usernames)
        usernames = list(set(usernames))  # Deduplicate

        if not usernames:
            logger.warning("No usernames extracted for lead %s", lead.id)
            return {
                "profiles": [],
                "footprint_score": 0.0,
                "usernames_checked": [],
                "scan_duration": 0.0,
            }

        # Scan each username
        all_results: list[SiteResult] = []
        for username in usernames:
            results = await self.scan_username(username)
            all_results.extend(results)

        # Deduplicate by platform (keep first found)
        seen_platforms = set()
        unique_profiles = []
        for r in all_results:
            if r.found and r.platform not in seen_platforms:
                seen_platforms.add(r.platform)
                unique_profiles.append(r)

        # Calculate footprint score
        footprint_score = self._calc_footprint_score(unique_profiles)

        duration = time.monotonic() - start_time
        logger.info(
            "Footprint scan complete for lead %s: %d profiles found in %.1fs",
            lead.id, len(unique_profiles), duration,
        )

        result = {
            "profiles": [
                {
                    "platform": p.platform,
                    "url": p.url,
                    "username": p.username,
                    "verified": p.found,
                    "category": p.category,
                    "sales_relevance": p.sales_relevance,
                }
                for p in unique_profiles
            ],
            "footprint_score": footprint_score,
            "usernames_checked": usernames,
            "scan_duration": round(duration, 2),
        }
        # ADDED (Phase 11): cache for CACHE_TTL_DAYS days
        try:
            await cache_set(ck, result)
        except Exception as exc:
            logger.debug("Footprint cache_set failed (non-fatal): %s", exc)
        return result

    async def _check_site(
        self,
        session: aiohttp.ClientSession,
        site_name: str,
        site_config: dict,
        username: str,
    ) -> SiteResult:
        """Check if a username exists on a specific site."""
        # Validate username against site regex
        regex = site_config.get("regexCheck")
        if regex:
            if not re.match(regex, username):
                return SiteResult(
                    platform=site_name,
                    url="",
                    username=username,
                    found=False,
                    error="regex_mismatch",
                )

        url = site_config["url"].replace("{}", username)
        url_probe = site_config.get("urlProbe", "").replace("{}", username) if site_config.get("urlProbe") else None
        check_url = url_probe or url

        error_type = site_config.get("errorType", "status_code")
        category = site_config.get("category", "unknown")
        relevance = site_config.get("sales_relevance", 0.5)

        # Rate limiting: add small random jitter
        await asyncio.sleep(random.uniform(0.1, 0.5))

        async with self._semaphore:
            start = time.monotonic()
            proxy = random.choice(self.proxy_pool) if self.proxy_pool else None

            try:
                method = site_config.get("request_method", "GET").upper()
                async with session.request(
                    method,
                    check_url,
                    proxy=proxy,
                    allow_redirects=(error_type != "response_url"),
                    ssl=False,
                ) as resp:
                    elapsed = (time.monotonic() - start) * 1000

                    found = False

                    if error_type == "status_code":
                        found = 200 <= resp.status < 300

                    elif error_type == "message":
                        body = await resp.text()
                        error_msgs = site_config.get("errorMsg", [])
                        if isinstance(error_msgs, str):
                            error_msgs = [error_msgs]
                        # If error message found in body, username does NOT exist
                        found = not any(msg in body for msg in error_msgs)

                    elif error_type == "response_url":
                        # If redirected away from the profile URL, username doesn't exist
                        found = str(resp.url).rstrip("/") == check_url.rstrip("/")

                    return SiteResult(
                        platform=site_name,
                        url=url,
                        username=username,
                        found=found,
                        category=category,
                        sales_relevance=relevance,
                        response_time_ms=elapsed,
                    )

            except asyncio.TimeoutError:
                return SiteResult(
                    platform=site_name, url=url, username=username,
                    found=False, category=category, sales_relevance=relevance,
                    error="timeout",
                )
            except aiohttp.ClientError as exc:
                return SiteResult(
                    platform=site_name, url=url, username=username,
                    found=False, category=category, sales_relevance=relevance,
                    error=str(exc),
                )
            except Exception as exc:
                logger.debug("Unexpected error checking %s for %s: %s", site_name, username, exc)
                return SiteResult(
                    platform=site_name, url=url, username=username,
                    found=False, category=category, sales_relevance=relevance,
                    error=str(exc),
                )

    # ADDED (Phase 11): IPRoyal residential proxy picker
    def _pick_iproyal_proxy(self) -> Optional[dict]:
        """Build a sticky-session IPRoyal residential proxy descriptor.

        Each call rotates ``session-{N}`` so consecutive HTTP requests
        come out of different residential exit IPs (still TR-geolocked).
        Returns ``None`` when IPRoyal is not configured — the scanner
        then falls back to its existing ``proxy_pool`` / direct path.
        """
        if not (settings.IPROYAL_USERNAME and settings.IPROYAL_PASSWORD):
            return None
        session_id = random.randint(1, max(settings.IPROYAL_POOL_SIZE, 1))
        return {
            "server": f"http://{settings.IPROYAL_ENDPOINT}",
            "username": f"{settings.IPROYAL_USERNAME}-session-{session_id}-country-tr",
            "password": settings.IPROYAL_PASSWORD,
        }

    def _calc_footprint_score(self, profiles: list[SiteResult]) -> float:
        """Calculate digital footprint score (0-100) based on discovered profiles.

        Scoring:
        - Each profile contributes based on its sales_relevance weight
        - Bonus for breadth across categories
        - Capped at 100
        """
        if not profiles:
            return 0.0

        # Base score: sum of relevance weights (max ~50 points)
        base = sum(p.sales_relevance * 10 for p in profiles)

        # Category diversity bonus (max ~20 points)
        categories = {p.category for p in profiles}
        diversity_bonus = len(categories) * 4

        # High-value platform bonus (max ~30 points)
        high_value = {"LinkedIn", "GitHub", "Twitter", "Medium", "Crunchbase", "ProductHunt"}
        hv_count = sum(1 for p in profiles if p.platform in high_value)
        hv_bonus = hv_count * 5

        score = min(100.0, base + diversity_bonus + hv_bonus)
        return round(score, 1)
