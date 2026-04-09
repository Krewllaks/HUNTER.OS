"""
HUNTER.OS - Account & Health Management API
Email accounts, LinkedIn accounts, warmup, blacklist.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.account import EmailAccount, LinkedInAccount, Blacklist
from app.schemas.account import (
    EmailAccountCreate, EmailAccountResponse,
    LinkedInAccountCreate, LinkedInAccountResponse,
    AccountHealthDashboard, BlacklistEntry, BlacklistResponse,
)
from app.core.encryption import encrypt_value
from app.services.warmup_service import WarmupService

router = APIRouter(prefix="/accounts", tags=["Accounts & Health"])


# ── Health Dashboard ─────────────────────────────────────
@router.get("/health", response_model=AccountHealthDashboard)
def get_health_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the Deliverability Health Dashboard."""
    warmup = WarmupService(db)
    dashboard_data = warmup.get_health_dashboard(current_user.id)

    email_accounts = db.query(EmailAccount).filter(
        EmailAccount.user_id == current_user.id
    ).all()
    linkedin_accounts = db.query(LinkedInAccount).filter(
        LinkedInAccount.user_id == current_user.id
    ).all()

    return AccountHealthDashboard(
        **dashboard_data,
        email_accounts=[EmailAccountResponse.model_validate(a) for a in email_accounts],
        linkedin_accounts=[LinkedInAccountResponse.model_validate(a) for a in linkedin_accounts],
    )


# ── Email Accounts ───────────────────────────────────────
@router.post("/email", response_model=EmailAccountResponse, status_code=201)
def add_email_account(
    req: EmailAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connect a new email account."""
    account = EmailAccount(
        user_id=current_user.id,
        email=req.email,
        provider=req.provider,
        smtp_host=req.smtp_host,
        smtp_port=req.smtp_port,
        smtp_user=req.smtp_user,
        smtp_password_encrypted=encrypt_value(req.smtp_password),
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        is_warming=True,
        warmup_day=0,
        daily_send_limit=5,  # Start conservative
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/email", response_model=list[EmailAccountResponse])
def list_email_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all connected email accounts."""
    accounts = db.query(EmailAccount).filter(
        EmailAccount.user_id == current_user.id
    ).all()
    return [EmailAccountResponse.model_validate(a) for a in accounts]


@router.post("/email/{account_id}/pause")
def pause_email_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause an email account."""
    account = db.query(EmailAccount).filter(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_paused = True
    account.pause_reason = "Manually paused by user"
    db.commit()
    return {"status": "paused"}


@router.post("/email/{account_id}/resume")
def resume_email_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused email account."""
    account = db.query(EmailAccount).filter(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_paused = False
    account.pause_reason = None
    db.commit()
    return {"status": "active"}


# ── LinkedIn Accounts ────────────────────────────────────
@router.post("/linkedin", response_model=LinkedInAccountResponse, status_code=201)
def add_linkedin_account(
    req: LinkedInAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connect a new LinkedIn account."""
    account = LinkedInAccount(
        user_id=current_user.id,
        linkedin_email=req.linkedin_email,
        session_cookie=encrypt_value(req.session_cookie),
        proxy_url=req.proxy_url,
        is_warming=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/linkedin", response_model=list[LinkedInAccountResponse])
def list_linkedin_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all connected LinkedIn accounts."""
    accounts = db.query(LinkedInAccount).filter(
        LinkedInAccount.user_id == current_user.id
    ).all()
    return [LinkedInAccountResponse.model_validate(a) for a in accounts]


# ── Blacklist (GDPR / Do Not Contact) ───────────────────
@router.get("/blacklist", response_model=list[BlacklistResponse])
def list_blacklist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all blacklisted domains/emails."""
    entries = db.query(Blacklist).filter(
        Blacklist.user_id == current_user.id
    ).order_by(Blacklist.added_at.desc()).all()
    return [BlacklistResponse.model_validate(e) for e in entries]


@router.post("/blacklist", response_model=BlacklistResponse, status_code=201)
def add_to_blacklist(
    req: BlacklistEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a domain or email to the blacklist."""
    if not req.domain and not req.email:
        raise HTTPException(status_code=400, detail="Must provide domain or email")

    entry = Blacklist(
        user_id=current_user.id,
        domain=req.domain,
        email=req.email,
        reason=req.reason,
        source="user_uploaded",
        region=req.region,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/blacklist/{entry_id}", status_code=204)
def remove_from_blacklist(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an entry from the blacklist."""
    entry = db.query(Blacklist).filter(
        Blacklist.id == entry_id,
        Blacklist.user_id == current_user.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    db.delete(entry)
    db.commit()
