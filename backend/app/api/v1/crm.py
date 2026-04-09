"""
HUNTER.OS - CRM Integration API
Export leads, create deals, sync status, check health.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.services.crm_service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM Integration"])


class CRMExportRequest(BaseModel):
    lead_ids: list[int]
    provider: str  # "hubspot" | "pipedrive"


class CRMDealRequest(BaseModel):
    crm_lead_id: str
    deal_name: str
    amount: float = 0
    provider: str


class CRMStatusSyncRequest(BaseModel):
    crm_id: str
    status: str
    provider: str


@router.post("/export")
async def export_leads(
    req: CRMExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export selected leads to CRM (HubSpot or Pipedrive)."""
    if req.provider not in ("hubspot", "pipedrive"):
        raise HTTPException(400, "Unsupported CRM provider. Use 'hubspot' or 'pipedrive'.")

    crm = CRMService(req.provider)
    health = await crm.check_health()
    if not health.get("healthy"):
        raise HTTPException(
            503,
            f"CRM provider '{req.provider}' is not configured or unreachable. "
            "Set the API key in .env.",
        )

    # Fetch leads owned by current user
    leads = (
        db.query(Lead)
        .filter(Lead.id.in_(req.lead_ids), Lead.user_id == current_user.id)
        .all()
    )

    if not leads:
        raise HTTPException(404, "No matching leads found.")

    lead_dicts = [
        {
            "first_name": l.first_name,
            "last_name": l.last_name,
            "email": l.email,
            "company_name": l.company_name,
            "company_domain": l.company_domain,
            "title": l.title,
            "phone": getattr(l, "phone", None),
            "status": l.status,
        }
        for l in leads
    ]

    results = await crm.export_leads_batch(lead_dicts)

    return {
        "exported": len([r for r in results if "error" not in r]),
        "errors": len([r for r in results if "error" in r]),
        "results": results,
    }


@router.post("/deal")
async def create_deal(
    req: CRMDealRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a deal in CRM linked to an exported contact."""
    crm = CRMService(req.provider)
    result = await crm.create_deal_for_lead(req.crm_lead_id, req.deal_name, req.amount)
    if not result:
        raise HTTPException(503, "CRM not configured.")
    if "error" in result:
        raise HTTPException(502, result["error"])
    return result


@router.post("/sync-status")
async def sync_status(
    req: CRMStatusSyncRequest,
    current_user: User = Depends(get_current_user),
):
    """Sync lead status to CRM."""
    crm = CRMService(req.provider)
    result = await crm.sync_status(req.crm_id, req.status)
    if not result:
        raise HTTPException(503, "CRM not configured.")
    if "error" in result:
        raise HTTPException(502, result["error"])
    return result


@router.get("/health")
async def crm_health(
    provider: str,
    current_user: User = Depends(get_current_user),
):
    """Check CRM provider connectivity."""
    crm = CRMService(provider)
    return await crm.check_health()
