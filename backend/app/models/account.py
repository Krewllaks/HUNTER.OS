"""
HUNTER.OS - Email/LinkedIn Account Management
Warm-up, Rotation, Health Tracking.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, JSON, Boolean, ForeignKey,
)
from app.core.database import Base


class EmailAccount(Base):
    """Connected email accounts for rotation & warm-up."""
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    email = Column(String(255), nullable=False)
    provider = Column(String(50))                   # gmail | outlook | smtp_custom
    smtp_host = Column(String(255))
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255))
    smtp_password_encrypted = Column(Text)          # AES encrypted
    imap_host = Column(String(255))
    imap_port = Column(Integer, default=993)

    # ── Warm-up State ────────────────────────────────────
    is_warming = Column(Boolean, default=True)
    warmup_day = Column(Integer, default=0)         # Current day in warmup cycle
    warmup_started_at = Column(DateTime)
    daily_send_limit = Column(Integer, default=5)   # Increases during warmup

    # ── Health Metrics ───────────────────────────────────
    total_sent_today = Column(Integer, default=0)
    total_sent_all = Column(Integer, default=0)
    bounce_rate = Column(Float, default=0.0)
    spam_complaint_rate = Column(Float, default=0.0)
    open_rate = Column(Float, default=0.0)
    health_score = Column(Float, default=100.0)     # 0-100, drops with bounces/spam

    # ── SPF/DKIM/DMARC ──────────────────────────────────
    spf_valid = Column(Boolean)
    dkim_valid = Column(Boolean)
    dmarc_valid = Column(Boolean)
    last_health_check = Column(DateTime)

    # ── Status ───────────────────────────────────────────
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)      # Pause if health drops
    pause_reason = Column(String(255))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class LinkedInAccount(Base):
    """Connected LinkedIn accounts for scraping & outreach."""
    __tablename__ = "linkedin_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    linkedin_email = Column(String(255), nullable=False)
    session_cookie = Column(Text)                   # li_at cookie (encrypted)
    proxy_url = Column(String(512))                 # Dedicated proxy per account

    # ── Warm-up ──────────────────────────────────────────
    is_warming = Column(Boolean, default=True)
    daily_connection_limit = Column(Integer, default=5)
    daily_message_limit = Column(Integer, default=10)
    daily_visit_limit = Column(Integer, default=25)

    # ── Usage Today ──────────────────────────────────────
    connections_sent_today = Column(Integer, default=0)
    messages_sent_today = Column(Integer, default=0)
    visits_today = Column(Integer, default=0)

    # ── Health ───────────────────────────────────────────
    health_score = Column(Float, default=100.0)
    last_restriction_date = Column(DateTime)
    restriction_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Blacklist(Base):
    """Do Not Contact list - GDPR/CAN-SPAM compliance."""
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    domain = Column(String(255), index=True)        # example.com
    email = Column(String(255), index=True)          # specific email
    reason = Column(String(255))                     # gdpr_request | unsubscribe | manual | bounce
    source = Column(String(100))                     # user_uploaded | auto_detected | api_sync
    region = Column(String(50))                      # EU | US | global
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
