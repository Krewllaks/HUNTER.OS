"""
HUNTER.OS - Lead Model
Core entity: every person/company the system hunts.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, JSON, Boolean, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_user_status", "user_id", "status"),
        Index("ix_leads_user_created", "user_id", "created_at"),
        Index("ix_leads_user_score", "user_id", "intent_score"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ── Identity ─────────────────────────────────────────
    first_name = Column(String(255))
    last_name = Column(String(255))
    email = Column(String(255), index=True)
    linkedin_url = Column(String(512))
    phone = Column(String(50))
    photo_url = Column(String(512))

    # ── Company ──────────────────────────────────────────
    company_name = Column(String(255), index=True)
    company_domain = Column(String(255))
    company_size = Column(String(50))       # "1-10", "11-50", ...
    industry = Column(String(255))
    company_location = Column(String(255))

    # ── Intelligence Signals ─────────────────────────────
    title = Column(String(255))             # Job title / role
    last_4_posts = Column(JSON, default=list)
    technographics = Column(JSON, default=list)     # ["Shopify", "Stripe", ...]
    recent_news = Column(JSON, default=list)        # [{headline, date, url}, ...]
    hiring_signals = Column(JSON, default=list)     # [{role, platform, date}, ...]
    website_changes = Column(JSON, default=list)    # [{change_type, detail, date}, ...]
    social_engagement = Column(JSON, default=list)  # [{platform, action, content}, ...]
    content_intent = Column(JSON, default=list)     # [{type, title, summary, url}, ...]

    # ── Personalization Data ─────────────────────────────
    communication_style = Column(String(50), default="formal")  # formal | casual | mixed
    hobbies = Column(JSON, default=list)
    common_ground = Column(JSON, default=list)      # [{type, detail}, ...]
    media_quotes = Column(JSON, default=list)       # [{source, quote, date}, ...]
    review_highlights = Column(JSON, default=list)  # [{platform, rating, snippet}, ...]

    # ── Scoring ──────────────────────────────────────────
    intent_score = Column(Float, default=0.0)       # 0-100
    confidence = Column(Float, default=0.0)         # 0-100 (how reliable the score is)
    icp_match_score = Column(Float, default=0.0)    # 0-100

    # ── Status ───────────────────────────────────────────
    status = Column(String(50), default="new")      # new | researched | contacted | replied | meeting | won | lost
    sentiment = Column(String(50))                  # positive | negative | neutral | objection
    objection_type = Column(String(100))            # price | timing | competitor | not_interested
    is_blacklisted = Column(Boolean, default=False)
    do_not_contact = Column(Boolean, default=False)

    # ── Digital Footprint (Sherlock-style scan) ────────────
    social_profiles = Column(JSON, default=list)     # [{platform, url, username, verified, category}]
    digital_footprint_score = Column(Float, default=0.0)  # 0-100 based on platform presence
    footprint_scanned_at = Column(DateTime, nullable=True)

    # ── Profile Cache (for cross-product reuse) ──────────
    profile_cache = Column(JSON, default=dict)      # Cached scraping data (posts, bio, experience)
    profile_data_cached_at = Column(DateTime, nullable=True)  # When cache was last updated

    # ── Metadata ─────────────────────────────────────────
    source = Column(String(100))                    # csv | linkedin_scrape | lookalike | manual
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    tags = Column(JSON, default=list)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # ── Soft Delete ──────────────────────────────────────
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    # ── Relationships ────────────────────────────────────
    buying_committee = relationship("BuyingCommittee", back_populates="lead", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="lead", cascade="all, delete-orphan")
    timing_patterns = relationship("TimingPattern", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    objection_logs = relationship("ObjectionLog", back_populates="lead", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="lead", cascade="all, delete-orphan")


class BuyingCommittee(Base):
    """Maps multiple decision-makers within a single lead's company."""
    __tablename__ = "buying_committee"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    role = Column(String(255))              # CEO, VP Sales, Head of Marketing
    email = Column(String(255))
    linkedin_url = Column(String(512))
    personalization_angle = Column(Text)    # AI-generated angle for this person
    communication_style = Column(String(50), default="formal")
    status = Column(String(50), default="not_contacted")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="buying_committee")


class TimingPattern(Base):
    """Learned optimal send times per lead."""
    __tablename__ = "timing_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)

    avg_open_hour = Column(Integer)         # 0-23
    best_day = Column(String(20))           # Monday, Tuesday, ...
    timezone = Column(String(50))
    confidence = Column(Float, default=0.0)
    open_history = Column(JSON, default=list)  # [{timestamp, channel}, ...]
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="timing_patterns")


class ObjectionLog(Base):
    """Tracks objections and AI-generated counter-arguments."""
    __tablename__ = "objection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    objection_type = Column(String(100), nullable=False)   # price | timing | competitor | authority | need
    objection_text = Column(Text)                          # Verbatim from lead
    counter_message = Column(Text)                         # AI-generated response
    outcome = Column(String(50))                           # accepted | rejected | pending
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="objection_logs")
