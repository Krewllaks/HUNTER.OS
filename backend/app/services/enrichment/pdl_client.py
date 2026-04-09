"""
HUNTER.OS - People Data Labs (PDL) Client (Phase 11)
================================================
Step 2 of the cost-optimised enrichment waterfall.

⚠️  IMPORTANT — PDL DOES NOT FIND EMAILS
----------------------------------------
PDL is a *profile enricher*, not an email finder. You give it an
existing identifier (email, LinkedIn URL, phone) and it returns the
full professional profile (skills, work history, education, etc.).

That is why in the Phase 11 waterfall PDL runs **after** Apollo:
1. Apollo finds the email.
2. PDL takes that email and fills in the rich profile.

Pricing
-------
* Free tier: **1,000 records / month**
* Docs: https://docs.peopledatalabs.com/docs/person-enrichment-api

Failure mode
------------
Returns ``None`` on missing key, missing input, 4xx/5xx, or empty
``data`` field. Caller continues without enrichment.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.cache import cache_get, cache_key, cache_set

logger = logging.getLogger(__name__)

_BASE_URL: str = "https://api.peopledatalabs.com/v5"
_DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class PDLClient:
    """
    Async client for People Data Labs ``/person/enrich``.

    Usage
    -----
    >>> client = PDLClient(api_key=settings.PDL_API_KEY)
    >>> profile = await client.enrich_person(email="ahmet@acme.com.tr")
    >>> if profile:
    ...     print(profile.get("job_title"), profile.get("skills"))
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    async def enrich_person(
        self,
        email: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Enrich an existing identity with full profile data.

        At least one of ``email`` or ``linkedin_url`` must be provided —
        PDL needs an anchor identifier; it does NOT search by name.

        Returns
        -------
        dict | None
            Selected, normalised profile fields:
            ``{"job_title", "job_company_name", "job_company_size",
            "linkedin_url", "twitter_url", "github_url", "skills",
            "interests", "summary", "location_country", "source": "pdl"}``.
            ``None`` on disabled key, missing input, or any failure.
        """
        if not self.api_key:
            logger.debug("PDL disabled (no API key)")
            return None

        email_norm = (email or "").strip().lower() or None
        linkedin_norm = (linkedin_url or "").strip() or None

        if not (email_norm or linkedin_norm):
            logger.debug("PDL skipped: no email or linkedin_url provided")
            return None

        ck = cache_key("pdl", email_norm, linkedin_norm)
        cached = await cache_get(ck)
        if cached:
            logger.info("PDL cache HIT for %s", email_norm or linkedin_norm)
            return cached

        params: dict[str, Any] = {"api_key": self.api_key, "min_likelihood": 6}
        if email_norm:
            params["email"] = email_norm
        if linkedin_norm:
            params["profile"] = linkedin_norm

        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as http:
                resp = await http.get(f"{_BASE_URL}/person/enrich", params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning("PDL network error: %s", exc)
            return None

        if resp.status_code == 401:
            logger.error("PDL 401: invalid API key")
            return None
        if resp.status_code == 402:
            logger.warning("PDL 402: free tier exhausted")
            return None
        if resp.status_code == 404:
            # PDL returns 404 when no person matches — that's a normal miss
            logger.info("PDL 404: no match for %s", email_norm or linkedin_norm)
            return None
        if resp.status_code == 429:
            logger.warning("PDL 429: rate-limited")
            return None
        if resp.status_code >= 400:
            logger.warning("PDL %d: %s", resp.status_code, resp.text[:200])
            return None

        try:
            payload = resp.json()
        except ValueError:
            logger.error("PDL returned non-JSON")
            return None

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return None

        result: dict[str, Any] = {
            "job_title": data.get("job_title"),
            "job_company_name": data.get("job_company_name"),
            "job_company_size": data.get("job_company_size"),
            "linkedin_url": data.get("linkedin_url"),
            "twitter_url": data.get("twitter_url"),
            "github_url": data.get("github_url"),
            "skills": data.get("skills") or [],
            "interests": data.get("interests") or [],
            "summary": data.get("summary"),
            "location_country": data.get("location_country"),
            "source": "pdl",
        }

        # Drop keys with falsy values to keep the cached blob compact
        result = {k: v for k, v in result.items() if v not in (None, [], "")}
        result["source"] = "pdl"

        await cache_set(ck, result)
        logger.info("PDL HIT for %s", email_norm or linkedin_norm)
        return result


__all__ = ["PDLClient"]
