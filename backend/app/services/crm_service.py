"""
HUNTER.OS - CRM Integration Layer
Supports HubSpot + Pipedrive. Push leads/contacts, create deals, sync status.
Pluggable via strategy pattern — add new CRMs without changing callers.
"""
import logging
import httpx
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Timeout for all CRM API calls (seconds)
_HTTP_TIMEOUT = 15.0


class CRMProvider(ABC):
    """Abstract CRM provider — implement for each CRM."""

    @abstractmethod
    async def push_lead(self, lead_data: dict) -> dict:
        """Push a lead/contact to the CRM. Returns CRM response with ID."""

    @abstractmethod
    async def create_deal(self, deal_data: dict) -> dict:
        """Create a deal/opportunity linked to a contact."""

    @abstractmethod
    async def update_status(self, crm_id: str, status: str) -> dict:
        """Update lead/deal status in the CRM."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify CRM API connectivity."""


class HubSpotProvider(CRMProvider):
    """HubSpot CRM v3 API integration."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def push_lead(self, lead_data: dict) -> dict:
        properties = {
            "email": lead_data.get("email", ""),
            "firstname": lead_data.get("first_name", ""),
            "lastname": lead_data.get("last_name", ""),
            "company": lead_data.get("company_name", ""),
            "jobtitle": lead_data.get("title", ""),
            "phone": lead_data.get("phone", ""),
            "website": lead_data.get("company_domain", ""),
            "hs_lead_status": _map_status_to_hubspot(lead_data.get("status", "new")),
        }
        # Remove empty values
        properties = {k: v for k, v in properties.items() if v}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{self.BASE_URL}/crm/v3/objects/contacts",
                json={"properties": properties},
                headers=self.headers,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"HubSpot contact created: {result.get('id')}")
            return {"crm": "hubspot", "crm_id": result.get("id"), "status": "created"}

    async def create_deal(self, deal_data: dict) -> dict:
        properties = {
            "dealname": deal_data.get("name", "New Deal"),
            "pipeline": deal_data.get("pipeline", "default"),
            "dealstage": deal_data.get("stage", "appointmentscheduled"),
            "amount": str(deal_data.get("amount", 0)),
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{self.BASE_URL}/crm/v3/objects/deals",
                json={"properties": properties},
                headers=self.headers,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"HubSpot deal created: {result.get('id')}")
            return {"crm": "hubspot", "deal_id": result.get("id"), "status": "created"}

    async def update_status(self, crm_id: str, status: str) -> dict:
        properties = {"hs_lead_status": _map_status_to_hubspot(status)}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.patch(
                f"{self.BASE_URL}/crm/v3/objects/contacts/{crm_id}",
                json={"properties": properties},
                headers=self.headers,
            )
            resp.raise_for_status()
            return {"crm": "hubspot", "crm_id": crm_id, "status": "updated"}

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/contacts?limit=1",
                    headers=self.headers,
                )
                return resp.status_code == 200
        except Exception:
            return False


class PipedriveProvider(CRMProvider):
    """Pipedrive CRM API v1 integration."""

    BASE_URL = "https://api.pipedrive.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _params(self, extra: dict = None) -> dict:
        params = {"api_token": self.api_key}
        if extra:
            params.update(extra)
        return params

    async def push_lead(self, lead_data: dict) -> dict:
        name = f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}".strip()
        payload = {
            "name": name or lead_data.get("company_name", "Unknown"),
            "email": [{"value": lead_data.get("email", ""), "primary": True}] if lead_data.get("email") else [],
            "org_id": None,
            "job_title": lead_data.get("title", ""),
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{self.BASE_URL}/persons",
                json=payload,
                params=self._params(),
            )
            resp.raise_for_status()
            result = resp.json()
            person_id = result.get("data", {}).get("id")
            logger.info(f"Pipedrive person created: {person_id}")
            return {"crm": "pipedrive", "crm_id": str(person_id), "status": "created"}

    async def create_deal(self, deal_data: dict) -> dict:
        payload = {
            "title": deal_data.get("name", "New Deal"),
            "value": deal_data.get("amount", 0),
            "currency": "USD",
            "person_id": deal_data.get("person_id"),
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{self.BASE_URL}/deals",
                json=payload,
                params=self._params(),
            )
            resp.raise_for_status()
            result = resp.json()
            deal_id = result.get("data", {}).get("id")
            logger.info(f"Pipedrive deal created: {deal_id}")
            return {"crm": "pipedrive", "deal_id": str(deal_id), "status": "created"}

    async def update_status(self, crm_id: str, status: str) -> dict:
        # Pipedrive doesn't have a native "lead status" on persons
        # Update the label field instead
        payload = {"label": _map_status_to_pipedrive(status)}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.put(
                f"{self.BASE_URL}/persons/{crm_id}",
                json=payload,
                params=self._params(),
            )
            resp.raise_for_status()
            return {"crm": "pipedrive", "crm_id": crm_id, "status": "updated"}

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/users/me",
                    params=self._params(),
                )
                return resp.status_code == 200
        except Exception:
            return False


# ── Status Mapping Helpers ─────────────────────────────────

def _map_status_to_hubspot(status: str) -> str:
    mapping = {
        "new": "NEW",
        "researched": "OPEN",
        "contacted": "IN_PROGRESS",
        "replied": "IN_PROGRESS",
        "meeting": "QUALIFIED",
        "won": "CONNECTED",
        "lost": "UNQUALIFIED",
    }
    return mapping.get(status, "NEW")


def _map_status_to_pipedrive(status: str) -> str:
    mapping = {
        "new": "New Lead",
        "researched": "Researched",
        "contacted": "Contacted",
        "replied": "Replied",
        "meeting": "Meeting Scheduled",
        "won": "Won",
        "lost": "Lost",
    }
    return mapping.get(status, "New Lead")


# ── Factory ────────────────────────────────────────────────

def get_crm_provider(provider_name: str) -> Optional[CRMProvider]:
    """Create a CRM provider instance from settings.

    Returns None if the required API key is not configured.
    """
    if provider_name == "hubspot":
        key = settings.HUBSPOT_API_KEY
        return HubSpotProvider(key) if key else None
    elif provider_name == "pipedrive":
        key = settings.PIPEDRIVE_API_KEY
        return PipedriveProvider(key) if key else None
    else:
        logger.warning(f"Unknown CRM provider: {provider_name}")
        return None


class CRMService:
    """High-level CRM service used by the rest of the app.

    Orchestrates push/sync across configured CRM providers.
    Gracefully no-ops if no CRM is configured.
    """

    def __init__(self, provider_name: Optional[str] = None):
        self.provider = get_crm_provider(provider_name) if provider_name else None

    async def export_lead(self, lead_data: dict) -> Optional[dict]:
        """Push a single lead to the configured CRM."""
        if not self.provider:
            return None
        try:
            return await self.provider.push_lead(lead_data)
        except Exception as e:
            logger.error(f"CRM export failed: {e}")
            return {"error": str(e)}

    async def export_leads_batch(self, leads: list[dict]) -> list[dict]:
        """Push multiple leads. Returns list of results."""
        results = []
        for lead in leads:
            result = await self.export_lead(lead)
            if result:
                results.append(result)
        return results

    async def create_deal_for_lead(
        self, crm_lead_id: str, deal_name: str, amount: float = 0
    ) -> Optional[dict]:
        """Create a deal linked to an exported lead."""
        if not self.provider:
            return None
        try:
            return await self.provider.create_deal({
                "name": deal_name,
                "amount": amount,
                "person_id": crm_lead_id,
            })
        except Exception as e:
            logger.error(f"CRM deal creation failed: {e}")
            return {"error": str(e)}

    async def sync_status(self, crm_id: str, status: str) -> Optional[dict]:
        """Sync lead status back to CRM."""
        if not self.provider:
            return None
        try:
            return await self.provider.update_status(crm_id, status)
        except Exception as e:
            logger.error(f"CRM status sync failed: {e}")
            return {"error": str(e)}

    async def check_health(self) -> dict:
        """Check CRM connectivity."""
        if not self.provider:
            return {"configured": False}
        healthy = await self.provider.health_check()
        return {
            "configured": True,
            "provider": type(self.provider).__name__,
            "healthy": healthy,
        }
