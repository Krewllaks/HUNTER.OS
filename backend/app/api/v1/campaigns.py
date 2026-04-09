"""
HUNTER.OS - Campaign API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignListResponse, CampaignAutopsyResponse,
)
from app.services.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all campaigns."""
    query = db.query(Campaign).filter(Campaign.user_id == current_user.id)
    if status:
        query = query.filter(Campaign.status == status)
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return CampaignListResponse(
        total=len(campaigns),
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
    )


@router.post("", response_model=CampaignResponse, status_code=201)
def create_campaign(
    req: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new campaign with workflow steps."""
    campaign = Campaign(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        icp_criteria=req.icp_criteria,
        workflow_steps=[s.model_dump() for s in req.workflow_steps],
        ab_variants=[v.model_dump() for v in req.ab_variants],
        tags=req.tags,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get campaign details."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id, Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    req: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update campaign settings."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id, Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = req.model_dump(exclude_unset=True)
    if "workflow_steps" in update_data and update_data["workflow_steps"]:
        update_data["workflow_steps"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in update_data["workflow_steps"]]
    if "ab_variants" in update_data and update_data["ab_variants"]:
        update_data["ab_variants"] = [v.model_dump() if hasattr(v, 'model_dump') else v for v in update_data["ab_variants"]]

    for field, value in update_data.items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/activate")
def activate_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate a campaign to start workflow processing."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id, Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not campaign.workflow_steps:
        raise HTTPException(status_code=400, detail="Campaign has no workflow steps defined")

    campaign.status = "active"
    db.commit()
    return {"status": "active", "message": f"Campaign '{campaign.name}' is now active"}


@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause an active campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id, Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "paused"
    db.commit()
    return {"status": "paused", "message": f"Campaign '{campaign.name}' is paused"}


@router.post("/{campaign_id}/enqueue/{lead_id}")
def enqueue_lead_to_campaign(
    campaign_id: int,
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a lead to a campaign's workflow."""
    engine = WorkflowEngine(db)
    workflow = engine.enqueue_lead(lead_id, campaign_id)
    return {"workflow_id": workflow.id, "status": workflow.status, "next_scheduled": workflow.next_scheduled}
