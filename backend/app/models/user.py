"""
HUNTER.OS - User Model (JWT + RBAC + Plan)
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="member")  # admin | manager | member
    is_active = Column(Boolean, default=True)

    # ── Plan & Billing ─────────────────────────────────
    plan = Column(String(50), default="trial")          # trial | pro | enterprise
    trial_started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    trial_ends_at = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=14))
    subscription_id = Column(String(255), nullable=True)  # LemonSqueezy/Stripe sub ID

    # ── Usage Tracking ─────────────────────────────────
    usage_this_month = Column(JSON, default=dict)       # {leads_discovered: 0, messages_sent: 0, ...}
    usage_reset_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
