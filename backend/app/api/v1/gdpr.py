"""
HUNTER.OS - GDPR Compliance Endpoints
Article 17 (Right to erasure) and Article 20 (Right to data portability).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.models.message import Message
from app.models.campaign import Workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


class ErasureRequest(BaseModel):
    email: str
    reason: str = "data_subject_request"


@router.post("/erasure")
def request_erasure(
    req: ErasureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR Article 17 - Right to erasure. Deletes all PII for a given email."""
    leads = db.query(Lead).filter(
        Lead.email == req.email,
        Lead.user_id == current_user.id,
    ).all()

    if not leads:
        raise HTTPException(status_code=404, detail="No data found for this email")

    erased_count = 0
    for lead in leads:
        # Delete all messages
        db.query(Message).filter(Message.lead_id == lead.id).delete()
        # Stop and delete workflows
        db.query(Workflow).filter(Workflow.lead_id == lead.id).delete()
        # Anonymize lead (keep record for audit trail, remove PII)
        lead.first_name = "[ERASED]"
        lead.last_name = "[ERASED]"
        lead.email = f"erased-{lead.id}@deleted.invalid"
        lead.linkedin_url = None
        lead.phone = None
        lead.company_domain = None
        lead.profile_cache = None
        lead.last_4_posts = None
        lead.is_blacklisted = True
        lead.do_not_contact = True
        erased_count += 1

    db.commit()
    logger.info(
        f"GDPR erasure completed: email={req.email}, "
        f"leads_erased={erased_count}, user_id={current_user.id}, "
        f"reason={req.reason}"
    )

    return {
        "status": "completed",
        "email": req.email,
        "leads_erased": erased_count,
        "reason": req.reason,
    }


@router.get("/export")
def export_data(
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR Article 20 - Right to data portability. Returns all stored data for an email."""
    leads = db.query(Lead).filter(
        Lead.email == email,
        Lead.user_id == current_user.id,
    ).all()

    if not leads:
        raise HTTPException(status_code=404, detail="No data found for this email")

    result = []
    for lead in leads:
        messages = db.query(Message).filter(Message.lead_id == lead.id).all()
        result.append({
            "lead": {
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "company_name": lead.company_name,
                "title": lead.title,
                "linkedin_url": lead.linkedin_url,
                "status": lead.status,
                "created_at": str(lead.created_at),
            },
            "messages": [
                {
                    "direction": msg.direction,
                    "channel": msg.channel,
                    "subject": msg.subject,
                    "body": msg.body,
                    "created_at": str(msg.created_at),
                }
                for msg in messages
            ],
        })

    return {"email": email, "data": result, "total_leads": len(result)}
