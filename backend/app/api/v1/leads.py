"""
HUNTER.OS - Lead Management API Endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead, BuyingCommittee
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadListResponse,
    LeadDetailResponse, BuyingCommitteeMember, BuyingCommitteeResponse,
)

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=LeadListResponse)
def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    search: str = Query(None),
    min_score: float = Query(None),
    sort_by: str = Query("intent_score"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List leads with filtering, search, and sorting."""
    query = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    )

    if status:
        query = query.filter(Lead.status == status)
    if min_score is not None:
        query = query.filter(Lead.intent_score >= min_score)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            Lead.first_name.ilike(search_term),
            Lead.last_name.ilike(search_term),
            Lead.company_name.ilike(search_term),
            Lead.email.ilike(search_term),
        ))

    total = query.count()

    # Sorting
    sort_col = getattr(Lead, sort_by, Lead.intent_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    leads = query.offset((page - 1) * per_page).limit(per_page).all()

    return LeadListResponse(
        total=total,
        page=page,
        per_page=per_page,
        leads=[LeadResponse.model_validate(l) for l in leads],
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full lead detail with all intelligence data."""
    lead = db.query(Lead).options(
        joinedload(Lead.buying_committee),
        joinedload(Lead.messages),
        joinedload(Lead.timing_patterns),
        joinedload(Lead.objection_logs),
    ).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    req: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead manually."""
    lead = Lead(user_id=current_user.id, **req.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    req: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update lead fields."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a lead (preserves audit trail)."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.is_deleted = True
    lead.deleted_at = datetime.now(timezone.utc)
    db.commit()


# ── Buying Committee ─────────────────────────────────────
@router.get("/{lead_id}/committee", response_model=list[BuyingCommitteeResponse])
def get_buying_committee(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get buying committee members for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id, Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.buying_committee


@router.post("/{lead_id}/committee", response_model=BuyingCommitteeResponse, status_code=201)
def add_committee_member(
    lead_id: int,
    req: BuyingCommitteeMember,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a buying committee member to a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id, Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    member = BuyingCommittee(lead_id=lead_id, **req.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
