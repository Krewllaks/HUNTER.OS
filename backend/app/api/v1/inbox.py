"""
HUNTER.OS - Unified Inbox API Endpoints
All channels (email, LinkedIn DM) in one stream.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.models.message import Message, Notification
from app.schemas.message import (
    MessageCreate, MessageResponse, InboxResponse,
    NotificationResponse, BridgeRequest,
)
from app.services.workflow_engine import WorkflowEngine
from app.services.bridge_service import BridgeService

router = APIRouter(prefix="/inbox", tags=["Unified Inbox"])


@router.get("/unified", response_model=InboxResponse)
def get_unified_inbox(
    channel: str = Query(None, description="Filter by channel: email, linkedin_dm, all"),
    direction: str = Query(None, description="Filter: inbound, outbound, all"),
    sentiment: str = Query(None, description="Filter: positive, negative, neutral"),
    is_read: bool = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified inbox: all messages across all channels in one view.
    AI auto-labels: positive, negative, neutral, meeting_request, price_inquiry.
    """
    query = db.query(Message).filter(Message.user_id == current_user.id)

    if channel and channel != "all":
        query = query.filter(Message.channel == channel)
    if direction and direction != "all":
        query = query.filter(Message.direction == direction)
    if sentiment:
        query = query.filter(Message.sentiment_label == sentiment)
    if is_read is not None:
        query = query.filter(Message.is_read == is_read)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            Message.body.ilike(search_term),
            Message.subject.ilike(search_term),
        ))

    total = query.count()
    unread = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
        Message.direction == "inbound",
    ).count()

    messages = query.order_by(Message.created_at.desc())\
        .offset((page - 1) * per_page).limit(per_page).all()

    # Enrich with lead data
    message_responses = []
    for msg in messages:
        lead = db.query(Lead).filter(Lead.id == msg.lead_id).first()
        resp = MessageResponse.model_validate(msg)
        if lead:
            resp.lead_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
            resp.lead_company = lead.company_name
            resp.lead_photo = lead.photo_url
        message_responses.append(resp)

    return InboxResponse(
        total=total,
        unread=unread,
        messages=message_responses,
    )


@router.get("/thread/{thread_id}", response_model=list[MessageResponse])
def get_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a conversation thread."""
    messages = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.thread_id == thread_id,
    ).order_by(Message.created_at.asc()).all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{message_id}/read")
def mark_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a message as read."""
    msg = db.query(Message).filter(
        Message.id == message_id,
        Message.user_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.is_read = True
    db.commit()
    return {"status": "read"}


@router.post("/compose", response_model=MessageResponse)
def compose_message(
    req: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compose and send a manual message."""
    msg = Message(
        user_id=current_user.id,
        lead_id=req.lead_id,
        direction="outbound",
        channel=req.channel,
        subject=req.subject,
        body=req.body,
        body_html=req.body_html,
        ai_generated=False,
        status="queued",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# ── Notifications ────────────────────────────────────────
@router.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notifications."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [NotificationResponse.model_validate(n) for n in notifications]


# ── Bridge to Telegram/WhatsApp ──────────────────────────
@router.post("/bridge/telegram-whatsapp")
async def bridge_notifications(
    req: BridgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bridge notifications to Telegram and/or WhatsApp."""
    bridge = BridgeService(db)
    result = await bridge.bridge_notifications(
        user_id=current_user.id,
        notification_ids=req.notification_ids,
        send_to=req.send_to,
        custom_message=req.message,
    )
    return result
