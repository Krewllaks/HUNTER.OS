"""
HUNTER.OS - HubSpot CRM Adapter.
Uses HubSpot API v3 via httpx.AsyncClient.
"""
import asyncio
import logging
from typing import Optional

import httpx

from .base import (
    BaseCRM,
    CRMContact,
    CRMDeal,
    CRMAuthError,
    CRMError,
    CRMRateLimitError,
)

logger = logging.getLogger(__name__)

HUBSPOT_BASE_URL = "https://api.hubapi.com"
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0


class HubSpotCRM(BaseCRM):
    """HubSpot CRM adapter (API v3)."""

    def __init__(self, api_key: str):
        if not api_key:
            raise CRMAuthError("hubspot", "API key is required")
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "hubspot"

    # ── HTTP helpers ────────────────────────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=HUBSPOT_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
    ) -> dict:
        """Execute an HTTP request with retry + exponential backoff."""
        client = self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, json=json_body)

                if resp.status_code == 401:
                    raise CRMAuthError("hubspot", "Invalid API key or token expired")
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "10"))
                    raise CRMRateLimitError("hubspot", retry_after=retry_after)
                if resp.status_code == 404:
                    return {}
                if resp.status_code >= 400:
                    body = resp.text[:500]
                    raise CRMError("hubspot", f"HTTP {resp.status_code}: {body}", resp.status_code)

                return resp.json() if resp.content else {}

            except (CRMAuthError, CRMRateLimitError):
                raise
            except CRMError as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    wait = INITIAL_BACKOFF_S * (2 ** (attempt - 1))
                    logger.warning(
                        "HubSpot request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, MAX_RETRIES, wait, exc.message,
                    )
                    await asyncio.sleep(wait)
            except httpx.HTTPError as exc:
                last_exc = CRMError("hubspot", f"Network error: {exc}")
                if attempt < MAX_RETRIES:
                    wait = INITIAL_BACKOFF_S * (2 ** (attempt - 1))
                    logger.warning(
                        "HubSpot network error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, MAX_RETRIES, wait, str(exc),
                    )
                    await asyncio.sleep(wait)

        raise last_exc or CRMError("hubspot", "Request failed after all retries")

    # ── BaseCRM implementation ──────────────────────────────

    async def test_connection(self) -> bool:
        """Verify credentials by fetching account info."""
        try:
            result = await self._request("GET", "/crm/v3/objects/contacts?limit=1")
            return "results" in result
        except CRMAuthError:
            return False
        except CRMError as exc:
            logger.error("HubSpot connection test failed: %s", exc.message)
            return False

    async def push_contact(self, contact: CRMContact) -> str:
        """Create or update a HubSpot contact."""
        properties = {
            "email": contact.email,
            "firstname": contact.first_name,
            "lastname": contact.last_name,
            "company": contact.company,
            "jobtitle": contact.title,
            "phone": contact.phone,
            "hs_lead_status": _map_status_to_hubspot(contact.status),
        }
        if contact.linkedin_url:
            properties["linkedin_url"] = contact.linkedin_url
        if contact.score:
            properties["hubspotscore"] = str(contact.score)

        # Merge custom fields
        for key, value in contact.custom_fields.items():
            properties[key] = str(value)

        # Remove empty values
        properties = {k: v for k, v in properties.items() if v}

        if contact.external_id:
            # Update existing
            result = await self._request(
                "PATCH",
                f"/crm/v3/objects/contacts/{contact.external_id}",
                json_body={"properties": properties},
            )
            ext_id = str(result.get("id", contact.external_id))
            logger.info("HubSpot contact updated: %s", ext_id)
            return ext_id
        else:
            # Create new
            result = await self._request(
                "POST",
                "/crm/v3/objects/contacts",
                json_body={"properties": properties},
            )
            ext_id = str(result.get("id", ""))
            if not ext_id:
                raise CRMError("hubspot", "Contact creation returned no ID")
            logger.info("HubSpot contact created: %s", ext_id)
            return ext_id

    async def push_deal(self, deal: CRMDeal) -> str:
        """Create a HubSpot deal."""
        properties = {
            "dealname": deal.title or "HUNTER.OS Lead",
            "amount": str(deal.value),
            "dealstage": _map_stage_to_hubspot(deal.stage),
            "pipeline": "default",
        }

        result = await self._request(
            "POST",
            "/crm/v3/objects/deals",
            json_body={"properties": properties},
        )
        ext_id = str(result.get("id", ""))
        if not ext_id:
            raise CRMError("hubspot", "Deal creation returned no ID")

        # Associate deal with contact if contact_id is provided
        if deal.contact_id:
            try:
                await self._request(
                    "PUT",
                    f"/crm/v3/objects/deals/{ext_id}/associations/contacts/{deal.contact_id}/deal_to_contact",
                    json_body={},
                )
            except CRMError as exc:
                logger.warning("Failed to associate deal %s with contact %s: %s", ext_id, deal.contact_id, exc.message)

        logger.info("HubSpot deal created: %s", ext_id)
        return ext_id

    async def get_contact(self, external_id: str) -> Optional[CRMContact]:
        """Fetch a HubSpot contact by ID."""
        props = "email,firstname,lastname,company,jobtitle,phone,hs_lead_status,linkedin_url"
        result = await self._request(
            "GET",
            f"/crm/v3/objects/contacts/{external_id}?properties={props}",
        )
        if not result or "id" not in result:
            return None
        return _parse_hubspot_contact(result)

    async def search_contact(self, email: str) -> Optional[CRMContact]:
        """Search HubSpot contacts by email."""
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
            "properties": [
                "email", "firstname", "lastname", "company",
                "jobtitle", "phone", "hs_lead_status", "linkedin_url",
            ],
            "limit": 1,
        }
        result = await self._request("POST", "/crm/v3/objects/contacts/search", json_body=body)
        results = result.get("results", [])
        if not results:
            return None
        return _parse_hubspot_contact(results[0])

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# ── Mapping helpers ─────────────────────────────────────────

_STATUS_MAP_TO_HUBSPOT = {
    "new": "NEW",
    "researched": "OPEN",
    "contacted": "IN_PROGRESS",
    "replied": "IN_PROGRESS",
    "meeting": "OPEN_DEAL",
    "won": "CONNECTED",
    "lost": "UNQUALIFIED",
}

_STAGE_MAP_TO_HUBSPOT = {
    "new": "appointmentscheduled",
    "qualified": "qualifiedtobuy",
    "proposal": "presentationscheduled",
    "negotiation": "decisionmakerboughtin",
    "won": "closedwon",
    "lost": "closedlost",
}


def _map_status_to_hubspot(status: str) -> str:
    return _STATUS_MAP_TO_HUBSPOT.get(status, "NEW")


def _map_stage_to_hubspot(stage: str) -> str:
    return _STAGE_MAP_TO_HUBSPOT.get(stage, "appointmentscheduled")


def _parse_hubspot_contact(data: dict) -> CRMContact:
    """Parse HubSpot API response into a CRMContact."""
    props = data.get("properties", {})
    return CRMContact(
        external_id=str(data.get("id", "")),
        email=props.get("email", ""),
        first_name=props.get("firstname", ""),
        last_name=props.get("lastname", ""),
        company=props.get("company", ""),
        title=props.get("jobtitle", ""),
        phone=props.get("phone", ""),
        linkedin_url=props.get("linkedin_url", ""),
        status=_reverse_status_from_hubspot(props.get("hs_lead_status", "")),
    )


def _reverse_status_from_hubspot(hs_status: str) -> str:
    """Map HubSpot lead status back to HUNTER.OS status."""
    reverse = {v: k for k, v in _STATUS_MAP_TO_HUBSPOT.items()}
    return reverse.get(hs_status, "new")
