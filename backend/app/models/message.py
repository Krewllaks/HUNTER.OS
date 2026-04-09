"""
HUNTER.OS - Message & Unified Inbox Models
All channels (email, LinkedIn DM, LinkedIn connect) in one stream.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Float
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class Message(Base):
    """Unified inbox: every inbound/outbound message across channels."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    # ── Direction & Channel ──────────────────────────────
    direction = Column(String(10), nullable=False)  # inbound | outbound
    channel = Column(String(50), nullable=False)    # email | linkedin_dm | linkedin_connect

    # ── Content ──────────────────────────────────────────
    subject = Column(String(500))
    body = Column(Text, nullable=False)
    body_html = Column(Text)

    # ── AI Metadata ──────────────────────────────────────
    ai_generated = Column(Boolean, default=False)
    personalization_data = Column(JSON, default=dict) 
    sentiment_label = Column(String(50))               
    sentiment_confidence = Column(Float, default=0.0)  # ARTIK TANIMLI
    auto_label = Column(String(50))                    

    # ── Tracking ─────────────────────────────────────────
    tracking_id = Column(String(255), index=True)   # UUID for open/click tracking
    sender_email = Column(String(255))               # Sender email address
    is_read = Column(Boolean, default=False)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)

    # ── Status ───────────────────────────────────────────
    status = Column(String(50), default="sent")     
    error_detail = Column(Text)

    # ── Thread ───────────────────────────────────────────
    thread_id = Column(String(255))
    in_reply_to = Column(Integer, ForeignKey("messages.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="messages")

class Notification(Base):
    """Bridge notifications to Telegram / WhatsApp."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    type = Column(String(50), nullable=False)
    title = Column(String(255))
    content = Column(Text, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)

    sent_to_telegram = Column(Boolean, default=False)
    sent_to_whatsapp = Column(Boolean, default=False)
    sent_at = Column(DateTime)

    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))