"""
HUNTER.OS - Lead Enrichment API Service
Integrates with external APIs: Hunter.io, Snov.io, FullContact, RocketReach, BuiltWith
to enrich lead data (email finding, company info, technographics).
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings
# ADDED (Phase 11): cache + free-tier providers (Apollo + PDL)
from app.core.cache import cache_get, cache_set, cache_key
from app.services.enrichment.apollo_client import ApolloClient
from app.services.enrichment.pdl_client import PDLClient

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class LeadEnrichmentAPI:
    """Orchestrates calls to multiple enrichment providers."""

    async def enrich_email(self, domain: str, first_name: str, last_name: str) -> dict:
        """Find professional email using cost-optimised waterfall (Phase 11).

        Order (cheapest → most expensive):
            1. **Apollo.io** (free 50/mo) — best free email finder
            2. **PDL** profile-enrich on the Apollo email (free 1000/mo)
            3. **Local guess + MX validation** ($0)
            4. **Hunter.io** (paid fallback)
            5. **Snov.io** (paid fallback)
            6. **RocketReach** (paid fallback)

        Results are cached for ``CACHE_TTL_DAYS`` so the same person
        is never billed twice. Signature is unchanged from Phase 1-10
        (``domain, first_name, last_name``) for full backward compat.
        """
        # ── Phase 11 cache check ─────────────────────────
        ck = cache_key("email", first_name or "", last_name or "", domain or "")
        cached = await cache_get(ck)
        if cached:
            return cached

        result: dict = {"email": None, "confidence": 0, "source": None}

        apollo = ApolloClient(api_key=settings.APOLLO_API_KEY) if settings.APOLLO_API_KEY else None
        pdl = PDLClient(api_key=settings.PDL_API_KEY) if settings.PDL_API_KEY else None

        # ── STEP 1: Apollo.io free tier (best signal) ────
        if apollo:
            try:
                hit = await apollo.find_email(
                    first_name=first_name, last_name=last_name, domain=domain
                )
                if hit and hit.get("email"):
                    result = hit
            except Exception as exc:
                logger.debug("Apollo failed: %s", exc)

        # ── STEP 2: PDL profile enrichment on found email ──
        if pdl and result.get("email"):
            try:
                enriched = await pdl.enrich_person(email=result["email"])
                if enriched:
                    # Merge profile fields without clobbering email/source
                    merged = dict(result)
                    for k, v in enriched.items():
                        if k not in ("email", "source") and v:
                            merged[k] = v
                    result = merged
            except Exception as exc:
                logger.debug("PDL enrichment failed: %s", exc)

        # ── STEP 3: Local pattern guess + MX validation ──
        if not result.get("email"):
            guess = self._guess_email_patterns(first_name, last_name, domain)
            if guess:
                result = guess

        # ── STEP 4: Hunter.io paid fallback ──────────────
        if not result.get("email") and settings.HUNTER_IO_API_KEY:
            try:
                hit = await self._hunter_email_finder(domain, first_name, last_name)
                if hit and hit.get("email"):
                    result = hit
            except Exception as exc:
                logger.debug("Hunter.io fallback failed: %s", exc)

        # ── STEP 5: Snov.io paid fallback ────────────────
        if not result.get("email") and settings.SNOV_IO_CLIENT_ID and settings.SNOV_IO_CLIENT_SECRET:
            try:
                hit = await self._snov_email_finder(domain, first_name, last_name)
                if hit and hit.get("email"):
                    result = hit
            except Exception as exc:
                logger.debug("Snov.io fallback failed: %s", exc)

        # ── STEP 6: RocketReach paid fallback ────────────
        if not result.get("email") and settings.ROCKETREACH_API_KEY:
            try:
                hit = await self._rocketreach_lookup(first_name, last_name, domain)
                if hit and hit.get("email"):
                    result = hit
            except Exception as exc:
                logger.debug("RocketReach fallback failed: %s", exc)

        # ── Cache only successful hits ───────────────────
        if result.get("email"):
            try:
                await cache_set(ck, result)
            except Exception as exc:
                logger.debug("Email cache_set failed (non-fatal): %s", exc)

        return result

    # ADDED (Phase 11): zero-cost local pattern guesser w/ MX validation
    def _guess_email_patterns(
        self, first: str, last: str, domain: str
    ) -> Optional[dict]:
        """Predict an email from common patterns and validate the MX.

        Returns a dict with ``email``, ``confidence`` (0-1), and
        ``source="local_guess"`` when the domain accepts mail. Returns
        ``None`` if the domain has no MX or DNS lookup fails — that
        way the waterfall keeps walking.
        """
        if not (first and last and domain):
            return None

        first_l = first.lower()
        last_l = last.lower()
        f, l = first_l[0], last_l[0]

        patterns = [
            f"{first_l}.{last_l}@{domain}",
            f"{first_l}{last_l}@{domain}",
            f"{first_l}_{last_l}@{domain}",
            f"{f}{last_l}@{domain}",
            f"{last_l}.{first_l}@{domain}",
            f"{last_l}{first_l}@{domain}",
            f"{first_l}@{domain}",
            f"info@{domain}",
            f"contact@{domain}",
        ]

        # MX validation — best-effort. dns.resolver may not be installed
        # in every environment, so swallow any exception and return None.
        try:
            import dns.resolver  # type: ignore
            mx = dns.resolver.resolve(domain, "MX", lifetime=3)
            if mx:
                return {
                    "email": patterns[0],
                    "confidence": 0.4,
                    "source": "local_guess",
                    "pattern_count": len(patterns),
                }
        except Exception as exc:
            logger.debug("MX lookup failed for %s: %s", domain, exc)

        return None

    async def enrich_person(self, email: str) -> dict:
        """Get person info from FullContact."""
        result: dict = {
            "name": None, "title": None, "company": None,
            "bio": None, "social_profiles": [], "source": None,
        }

        if settings.FULLCONTACT_API_KEY:
            try:
                fc = await self._fullcontact_enrich(email)
                if fc:
                    return fc
            except Exception as exc:
                logger.debug("FullContact failed: %s", exc)

        return result

    async def enrich_company(self, domain: str) -> dict:
        """Get company technographics from BuiltWith."""
        result: dict = {
            "technologies": [], "tech_spend_estimate": None,
            "category_summary": {}, "source": None,
        }

        if settings.BUILTWITH_API_KEY:
            try:
                bw = await self._builtwith_lookup(domain)
                if bw:
                    return bw
            except Exception as exc:
                logger.debug("BuiltWith failed: %s", exc)

        return result

    async def full_enrich(
        self,
        domain: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict:
        """Run all available enrichments and merge results."""
        result: dict = {
            "email_found": None,
            "person": {},
            "company": {},
            "providers_used": [],
        }

        # Email finding
        if domain and first_name and last_name and not email:
            email_data = await self.enrich_email(domain, first_name, last_name)
            if email_data.get("email"):
                result["email_found"] = email_data["email"]
                result["providers_used"].append(email_data.get("source"))

        # Person enrichment
        target_email = email or result.get("email_found")
        if target_email:
            person = await self.enrich_person(target_email)
            if person.get("source"):
                result["person"] = person
                result["providers_used"].append(person["source"])

        # Company enrichment
        if domain:
            company = await self.enrich_company(domain)
            if company.get("source"):
                result["company"] = company
                result["providers_used"].append(company["source"])

        return result

    # ── Hunter.io ──────────────────────────────────────────────

    async def _hunter_email_finder(
        self, domain: str, first_name: str, last_name: str
    ) -> Optional[dict]:
        """https://hunter.io/api-documentation/v2#email-finder"""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": settings.HUNTER_IO_API_KEY,
                },
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                if data.get("email"):
                    return {
                        "email": data["email"],
                        "confidence": data.get("score", 0),
                        "source": "hunter.io",
                        "type": data.get("type"),  # personal or generic
                        "position": data.get("position"),
                        "company": data.get("company"),
                    }
            elif resp.status_code == 429:
                logger.warning("Hunter.io rate limit hit")
            else:
                logger.debug("Hunter.io %d: %s", resp.status_code, resp.text[:200])
        return None

    # ── Snov.io ────────────────────────────────────────────────

    async def _snov_get_token(self, client: httpx.AsyncClient) -> Optional[str]:
        """Get OAuth token from Snov.io."""
        resp = await client.post(
            "https://api.snov.io/v1/oauth/access_token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.SNOV_IO_CLIENT_ID,
                "client_secret": settings.SNOV_IO_CLIENT_SECRET,
            },
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        return None

    async def _snov_email_finder(
        self, domain: str, first_name: str, last_name: str
    ) -> Optional[dict]:
        """https://snov.io/knowledgebase/api-documentation"""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            token = await self._snov_get_token(client)
            if not token:
                return None

            resp = await client.post(
                "https://api.snov.io/v1/get-emails-from-names",
                json={
                    "access_token": token,
                    "firstName": first_name,
                    "lastName": last_name,
                    "domain": domain,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                emails = data.get("data", {}).get("emails", [])
                if emails:
                    best = max(emails, key=lambda e: e.get("emailStatusInt", 0))
                    return {
                        "email": best.get("email"),
                        "confidence": best.get("emailStatusInt", 0) * 20,
                        "source": "snov.io",
                    }
        return None

    # ── RocketReach ────────────────────────────────────────────

    async def _rocketreach_lookup(
        self, first_name: str, last_name: str, domain: str
    ) -> Optional[dict]:
        """https://rocketreach.co/api/docs"""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                "https://api.rocketreach.co/api/v2/person/lookup",
                params={
                    "name": f"{first_name} {last_name}",
                    "current_employer": domain.replace("www.", "").split(".")[0],
                },
                headers={"Api-Key": settings.ROCKETREACH_API_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                emails = data.get("emails", [])
                if emails:
                    return {
                        "email": emails[0].get("email") if isinstance(emails[0], dict) else emails[0],
                        "confidence": 80,
                        "source": "rocketreach",
                        "title": data.get("current_title"),
                        "linkedin": data.get("linkedin_url"),
                    }
        return None

    # ── FullContact ────────────────────────────────────────────

    async def _fullcontact_enrich(self, email: str) -> Optional[dict]:
        """https://docs.fullcontact.com/docs/enrich-overview"""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                "https://api.fullcontact.com/v3/person.enrich",
                json={"email": email},
                headers={"Authorization": f"Bearer {settings.FULLCONTACT_API_KEY}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                socials = []
                for s in data.get("socialProfiles", []) or data.get("details", {}).get("profiles", []):
                    if isinstance(s, dict):
                        socials.append({
                            "platform": s.get("type") or s.get("service", "unknown"),
                            "url": s.get("url", ""),
                            "username": s.get("username", ""),
                        })

                return {
                    "name": data.get("fullName"),
                    "title": data.get("title") or data.get("organization", {}).get("title"),
                    "company": data.get("organization", {}).get("name"),
                    "bio": data.get("bio"),
                    "social_profiles": socials,
                    "source": "fullcontact",
                    "avatar": data.get("avatar"),
                    "location": data.get("location"),
                }
            elif resp.status_code == 404:
                logger.debug("FullContact: person not found for %s", email)
            elif resp.status_code == 429:
                logger.warning("FullContact rate limit hit")
        return None

    # ── BuiltWith ──────────────────────────────────────────────

    async def _builtwith_lookup(self, domain: str) -> Optional[dict]:
        """https://api.builtwith.com/"""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                "https://api.builtwith.com/free1/api.json",
                params={
                    "KEY": settings.BUILTWITH_API_KEY,
                    "LOOKUP": domain,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                groups = data.get("groups", []) or data.get("Results", [{}])[0].get("Result", {}).get("Paths", [{}])[0].get("Technologies", [])
                techs = []
                categories: dict[str, int] = {}

                for item in groups:
                    if isinstance(item, dict):
                        cats = item.get("categories", [])
                        if not isinstance(cats, list):
                            cats = []
                        for cat in cats:
                            if isinstance(cat, dict):
                                live = cat.get("live", []) or cat.get("LiveTechnologies", [])
                                if not isinstance(live, list):
                                    live = []
                                cat_name = cat.get("name", "Other")
                                categories[cat_name] = categories.get(cat_name, 0) + len(live)
                                for tech in live:
                                    if isinstance(tech, dict):
                                        techs.append({
                                            "name": tech.get("Name") or tech.get("name", ""),
                                            "category": cat_name,
                                            "first_detected": tech.get("FirstDetected"),
                                        })
                                    elif isinstance(tech, str):
                                        techs.append({"name": tech, "category": cat_name})
                    elif isinstance(item, str):
                        techs.append({"name": item, "category": "Other"})

                if techs or categories:
                    return {
                        "technologies": techs[:50],
                        "tech_spend_estimate": None,
                        "category_summary": categories,
                        "source": "builtwith",
                    }
        return None
