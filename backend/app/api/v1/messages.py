"""
HUNTER.OS - Message Generation & Preview API
Generate personalized messages, preview, approve, and batch process.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.models.message import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])


class GenerateMessageRequest(BaseModel):
    channel: str = "email"
    campaign_context: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    lead_ids: list[int]
    channel: str = "email"
    campaign_context: Optional[str] = None


class ApproveMessageRequest(BaseModel):
    body: str
    subject_line: Optional[str] = None
    channel: str = "email"


@router.post("/{lead_id}/generate")
async def generate_message(
    lead_id: int,
    req: GenerateMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a personalized message for a lead using content analysis + personalization."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id, Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Build lead data dict
    lead_data = _lead_to_dict(lead)

    # Step 1: Content analysis
    from app.agents.content_analyst_agent import ContentAnalystAgent
    analyst = ContentAnalystAgent()
    content_profile = await analyst.analyze(lead_data)

    # Step 2: Merge content profile into lead data for personalization
    lead_data["content_profile"] = content_profile

    # Step 3: Generate personalized message
    from app.agents.personalization_agent import PersonalizationAgent
    personalizer = PersonalizationAgent()
    message = await personalizer.generate_message(
        lead_data=lead_data,
        channel=req.channel,
        campaign_context=req.campaign_context,
    )

    # Store content profile on lead for future use
    lead.communication_style = content_profile.get("communication_style", lead.communication_style)
    if content_profile.get("interests_hobbies"):
        lead.hobbies = content_profile["interests_hobbies"]
    db.commit()

    return {
        "lead_id": lead_id,
        "message": message,
        "content_profile": content_profile,
        "channel": req.channel,
    }


@router.post("/{lead_id}/approve")
def approve_message(
    lead_id: int,
    req: ApproveMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a generated message and save it for sending."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id, Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    msg = Message(
        lead_id=lead.id,
        direction="outbound",
        channel=req.channel,
        subject=req.subject_line,
        body=req.body,
        status="approved",
        sender_email=current_user.email,
    )
    db.add(msg)

    # Update lead status
    if lead.status == "new" or lead.status == "researched":
        lead.status = "contacted"

    db.commit()
    db.refresh(msg)

    return {"message_id": msg.id, "status": "approved", "lead_id": lead_id}


def _batch_generate_background(lead_ids: list[int], user_id: int, channel: str, campaign_context: str | None):
    """Background task for batch message generation.

    Uses _run_async() to safely call async agents from this sync background
    context, whether or not an event loop is already running in the thread.
    """
    import asyncio
    import concurrent.futures
    from app.agents.content_analyst_agent import ContentAnalystAgent
    from app.agents.personalization_agent import PersonalizationAgent

    def _run_async(coro):
        """Run async coroutine from sync context safely."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        else:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=120)

    db = SessionLocal()
    try:
        analyst = ContentAnalystAgent()
        personalizer = PersonalizationAgent()

        results = []
        for lead_id in lead_ids:
            lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == user_id).first()
            if not lead:
                continue

            lead_data = _lead_to_dict(lead)

            try:
                content_profile = _run_async(analyst.analyze(lead_data))
                lead_data["content_profile"] = content_profile

                message = _run_async(personalizer.generate_message(
                    lead_data=lead_data,
                    channel=channel,
                    campaign_context=campaign_context,
                ))

                # Save as draft message
                msg = Message(
                    lead_id=lead.id,
                    direction="outbound",
                    channel=channel,
                    subject=message.get("subject_line"),
                    body=message.get("body", ""),
                    status="draft",
                    personalization_data=message,
                    sender_email="",
                )
                db.add(msg)

                # Update lead communication style
                lead.communication_style = content_profile.get("communication_style", lead.communication_style)
                db.commit()

                results.append({"lead_id": lead_id, "status": "generated"})
            except Exception as e:
                logger.error(f"Batch generation failed for lead {lead_id}: {e}")
                results.append({"lead_id": lead_id, "status": "failed", "error": str(e)})

        logger.info(f"Batch generation complete: {len(results)} messages processed")
    finally:
        db.close()


@router.post("/batch-generate")
def batch_generate(
    req: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate personalized messages for multiple leads in background."""
    # Validate lead IDs belong to user
    valid_leads = db.query(Lead.id).filter(
        Lead.id.in_(req.lead_ids),
        Lead.user_id == current_user.id,
    ).all()
    valid_ids = [l[0] for l in valid_leads]

    if not valid_ids:
        raise HTTPException(status_code=400, detail="No valid lead IDs provided")

    background_tasks.add_task(
        _batch_generate_background,
        valid_ids, current_user.id, req.channel, req.campaign_context,
    )

    return {
        "status": "processing",
        "total_leads": len(valid_ids),
        "message": f"Generating messages for {len(valid_ids)} leads in background",
    }


@router.get("/{lead_id}/drafts")
def get_lead_drafts(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get draft/approved messages for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id, Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    messages = db.query(Message).filter(
        Message.lead_id == lead_id,
        Message.status.in_(["draft", "approved"]),
    ).order_by(Message.created_at.desc()).all()

    return {
        "lead_id": lead_id,
        "messages": [
            {
                "id": m.id,
                "channel": m.channel,
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "personalization_data": m.personalization_data,
                "created_at": str(m.created_at),
            }
            for m in messages
        ],
    }


def _lead_to_dict(lead: Lead) -> dict:
    """Convert Lead model to dict for AI agents."""
    return {
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "linkedin_url": lead.linkedin_url,
        "company_name": lead.company_name,
        "company_domain": lead.company_domain,
        "industry": lead.industry,
        "title": lead.title,
        "company_size": lead.company_size,
        "last_4_posts": lead.last_4_posts or [],
        "technographics": lead.technographics or [],
        "recent_news": lead.recent_news or [],
        "hiring_signals": lead.hiring_signals or [],
        "website_changes": lead.website_changes or [],
        "social_engagement": lead.social_engagement or [],
        "content_intent": lead.content_intent or [],
        "communication_style": lead.communication_style,
        "hobbies": lead.hobbies or [],
        "common_ground": lead.common_ground or [],
        "media_quotes": lead.media_quotes or [],
        "intent_score": lead.intent_score,
        "icp_match_score": lead.icp_match_score,
    }
