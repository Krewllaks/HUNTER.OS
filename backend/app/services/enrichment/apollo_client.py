"""
HUNTER.OS - Apollo.io Client (Phase 11)
================================================
Step 1 of the cost-optimised enrichment waterfall.

Pricing
-------
* Free tier: **50 people-match calls / month**
* Paid: $49+/month for higher quotas
* Docs: https://apolloapi.io/

Why Apollo first?
-----------------
Of the free email-finder providers in 2026, Apollo has by far the
deepest professional contact database (275M+ contacts) AND a usable
free tier. We try Apollo BEFORE any paid provider (Hunter, Snov,
RocketReach) so the average lead costs $0 to enrich.

Endpoint
--------
``POST https://api.apollo.io/v1/people/match``

Auth: ``X-API-Key`` header.

Failure mode
------------
Returns ``None`` on missing key, 401, 429, network error, or empty
response. Caller (``LeadEnrichmentAPI.enrich_email``) falls through
to the next waterfall step (PDL → local guess → Hunter → Snov).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.cache import cache_get, cache_key, cache_set

logger = logging.getLogger(__name__)

_BASE_URL: str = "https://api.apollo.io/v1"
_DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class ApolloClient:
    """
    Async client for Apollo.io people-match (email finder).

    Usage
    -----
    >>> client = ApolloClient(api_key=settings.APOLLO_API_KEY)
    >>> result = await client.find_email("Ahmet", "Yilmaz", "acme.com.tr")
    >>> if result:
    ...     print(result["email"], result.get("title"))
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> Optional[dict[str, Any]]:
        """
        Look up a verified business email + light profile data.

        Parameters
        ----------
        first_name, last_name, domain : str
            Required identifiers. Empty / whitespace inputs short-circuit
            to ``None`` so the waterfall stays cheap.

        Returns
        -------
        dict | None
            ``{"email", "title", "linkedin_url", "first_name",
            "last_name", "company", "source": "apollo"}`` on success.
            ``None`` if the API key is missing, the call fails, or
            no person was matched.
        """
        if not self.api_key:
            logger.debug("Apollo disabled (no API key)")
            return None

        first = (first_name or "").strip()
        last = (last_name or "").strip()
        dom = (domain or "").strip().lower()
        if not (first and last and dom):
            return None

        ck = cache_key("apollo", first, last, dom)
        cached = await cache_get(ck)
        if cached:
            logger.info("Apollo cache HIT for %s %s @ %s", first, last, dom)
            return cached

        payload = {
            "first_name": first,
            "last_name": last,
            "domain": dom,
            # Hint Apollo to reveal personal email when available
            "reveal_personal_emails": False,
        }
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as http:
                resp = await http.post(
                    f"{_BASE_URL}/people/match",
                    json=payload,
                    headers=headers,
                )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning("Apollo network error: %s", exc)
            return None

        if resp.status_code == 401:
            logger.error("Apollo 401: invalid API key")
            return None
        if resp.status_code == 429:
            logger.warning("Apollo 429: rate-limited (free tier exhausted?)")
            return None
        if resp.status_code >= 400:
            logger.warning("Apollo %d: %s", resp.status_code, resp.text[:200])
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.error("Apollo returned non-JSON")
            return None

        person = data.get("person") if isinstance(data, dict) else None
        if not isinstance(person, dict):
            return None

        email = person.get("email")
        if not email:
            # Apollo found a profile but no email — not useful for outreach
            logger.info("Apollo matched profile but no email for %s %s", first, last)
            return None

        org = person.get("organization") or {}
        result: dict[str, Any] = {
            "email": email,
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
            "first_name": person.get("first_name") or first,
            "last_name": person.get("last_name") or last,
            "company": (org.get("name") if isinstance(org, dict) else None),
            "source": "apollo",
        }

        await cache_set(ck, result)
        logger.info("Apollo HIT for %s %s @ %s", first, last, dom)
        return result


__all__ = ["ApolloClient"]
