"""
HUNTER.OS - Campaign & Workflow Models
Logic-based workflows with decision-tree flows.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, JSON, Boolean, ForeignKey,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Campaign(Base):
    """A campaign groups leads + workflow logic + message variants."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="draft")  # draft | active | paused | completed

    # ── ICP Definition ───────────────────────────────────
    icp_criteria = Column(JSON, default=dict)      # {industry, size, tech, signals...}

    # ── Workflow Logic (Decision Tree) ───────────────────
    workflow_steps = Column(JSON, default=list)
    # Example:
    # [
    #   {"step": 1, "channel": "linkedin_visit", "delay_hours": 0},
    #   {"step": 2, "channel": "email", "delay_hours": 24, "template_id": "intro_a"},
    #   {"step": 3, "channel": "linkedin_connect", "delay_hours": 48},
    #   {"step": 4, "channel": "email", "delay_hours": 72, "template_id": "follow_up_a",
    #    "condition": {"if": "email_opened", "then": "proceed", "else": "skip_to_step_6"}},
    # ]

    # ── A/B Testing ──────────────────────────────────────
    ab_variants = Column(JSON, default=list)       # [{variant_id, template, weight}, ...]
    winning_variant = Column(String(100))

    # ── Analytics Snapshot ───────────────────────────────
    total_leads = Column(Integer, default=0)
    total_contacted = Column(Integer, default=0)
    total_replied = Column(Integer, default=0)
    total_meetings = Column(Integer, default=0)
    reply_rate = Column(Float, default=0.0)
    meeting_rate = Column(Float, default=0.0)

    # ── Metadata ─────────────────────────────────────────
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    leads = relationship("Lead", backref="campaign", foreign_keys="Lead.campaign_id")
    workflows = relationship("Workflow", back_populates="campaign", cascade="all, delete-orphan")
    analytics = relationship("CampaignAnalytics", back_populates="campaign", cascade="all, delete-orphan")


class Workflow(Base):
    """Tracks each lead's position within a campaign's workflow."""
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)

    current_step = Column(Integer, default=1)
    status = Column(String(50), default="active")  # active | paused | completed | stopped_reply
    last_action = Column(String(100))               # linkedin_visit | email_sent | dm_sent
    last_action_at = Column(DateTime)
    next_scheduled = Column(DateTime)
    ab_variant_assigned = Column(String(100))

    # ── Event Log ────────────────────────────────────────
    event_log = Column(JSON, default=list)
    # [{timestamp, action, channel, result, detail}, ...]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="workflows")
    campaign = relationship("Campaign", back_populates="workflows")


class CampaignAnalytics(Base):
    """Per-variant, per-day analytics for Campaign Autopsy."""
    __tablename__ = "campaign_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)

    date = Column(DateTime, nullable=False)
    variant = Column(String(100))
    channel = Column(String(50))                    # email | linkedin | dm

    sent = Column(Integer, default=0)
    opened = Column(Integer, default=0)
    clicked = Column(Integer, default=0)
    replied = Column(Integer, default=0)
    positive_replies = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    revenue_attributed = Column(Float, default=0.0)

    # Best performing signals
    top_signal = Column(String(100))                # hiring_intent | technographics | ...
    top_day = Column(String(20))
    top_hour = Column(Integer)

    campaign = relationship("Campaign", back_populates="analytics")
