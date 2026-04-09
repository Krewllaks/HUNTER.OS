"""
HUNTER.OS - Message & Inbox Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MessageCreate(BaseModel):
    lead_id: int
    channel: str                # email | linkedin_dm
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    lead_id: int
    direction: str
    channel: str
    subject: Optional[str]
    body: str
    ai_generated: bool
    sentiment_label: Optional[str]
    auto_label: Optional[str]
    is_read: bool
    status: str
    thread_id: Optional[str]
    created_at: datetime

    # Lead context (for inbox view)
    lead_name: Optional[str] = None
    lead_company: Optional[str] = None
    lead_photo: Optional[str] = None

    model_config = {"from_attributes": True}


class InboxResponse(BaseModel):
    total: int
    unread: int
    messages: list[MessageResponse]


class InboxFilters(BaseModel):
    channel: Optional[str] = None       # email | linkedin_dm | all
    direction: Optional[str] = None     # inbound | outbound | all
    sentiment: Optional[str] = None     # positive | negative | neutral
    is_read: Optional[bool] = None
    search: Optional[str] = None
    page: int = 1
    per_page: int = 50


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: Optional[str]
    content: str
    is_read: bool
    sent_to_telegram: bool
    sent_to_whatsapp: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BridgeRequest(BaseModel):
    """POST /api/v1/bridge/telegram-whatsapp"""
    notification_ids: list[int] = []
    send_to: list[str] = ["telegram"]   # telegram | whatsapp
    message: Optional[str] = None       # Custom message override
