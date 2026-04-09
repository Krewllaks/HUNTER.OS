"""HUNTER.OS - Audit Log Model for enterprise compliance (SOC2/GDPR)."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Index
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
        Index("ix_audit_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)  # nullable for system actions
    action = Column(String(100), nullable=False)  # create, update, delete, login, export, etc.
    resource_type = Column(String(100), nullable=False)  # lead, campaign, message, user, etc.
    resource_id = Column(String(100), nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    detail = Column(Text, nullable=True)  # Human-readable description
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
