"""
HUNTER.OS - Account & Health Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EmailAccountCreate(BaseModel):
    email: str
    provider: str = "gmail"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: int = 993


class EmailAccountResponse(BaseModel):
    id: int
    email: str
    provider: str
    is_warming: bool
    warmup_day: int
    daily_send_limit: int
    total_sent_today: int
    bounce_rate: float
    spam_complaint_rate: float
    open_rate: float
    health_score: float
    spf_valid: Optional[bool]
    dkim_valid: Optional[bool]
    dmarc_valid: Optional[bool]
    is_active: bool
    is_paused: bool
    pause_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkedInAccountCreate(BaseModel):
    linkedin_email: str
    session_cookie: Optional[str] = None
    proxy_url: Optional[str] = None


class LinkedInAccountResponse(BaseModel):
    id: int
    linkedin_email: str
    is_warming: bool
    daily_connection_limit: int
    daily_message_limit: int
    daily_visit_limit: int
    connections_sent_today: int
    messages_sent_today: int
    visits_today: int
    health_score: float
    is_active: bool
    is_paused: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountHealthDashboard(BaseModel):
    """Deliverability Health Dashboard overview."""
    total_email_accounts: int
    total_linkedin_accounts: int
    avg_email_health: float
    avg_linkedin_health: float
    accounts_warming: int
    accounts_paused: int
    total_sent_today: int
    total_daily_capacity: int
    email_accounts: list[EmailAccountResponse]
    linkedin_accounts: list[LinkedInAccountResponse]
    warnings: list[str]                # ["Account X bounce rate > 5%", ...]


class BlacklistEntry(BaseModel):
    domain: Optional[str] = None
    email: Optional[str] = None
    reason: str = "manual"
    region: str = "global"


class BlacklistResponse(BaseModel):
    id: int
    domain: Optional[str]
    email: Optional[str]
    reason: str
    source: str
    region: str
    added_at: datetime

    model_config = {"from_attributes": True}
