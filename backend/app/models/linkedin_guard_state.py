"""
HUNTER.OS - LinkedIn Guard State Model
Persists rate limiting state for LinkedInGuard across restarts and workers.
"""
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, JSON, UniqueConstraint,
)
from app.core.database import Base


class LinkedInGuardState(Base):
    __tablename__ = "linkedin_guard_states"
    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_account_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, default=lambda: date.today())
    action_counts = Column(JSON, default=dict)
    paused_until = Column(DateTime, nullable=True)
    pause_reason = Column(String, nullable=True)
    session_started_at = Column(DateTime, nullable=True)
    session_action_count = Column(Integer, default=0)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
