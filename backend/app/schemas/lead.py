"""
HUNTER.OS - Lead Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = "manual"
    tags: list[str] = []
    notes: Optional[str] = None


VALID_LEAD_STATUSES = {"new", "researched", "contacted", "replied", "meeting", "won", "lost"}


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    do_not_contact: Optional[bool] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_LEAD_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {', '.join(sorted(VALID_LEAD_STATUSES))}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v is not None and v != "" and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class LeadResponse(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    linkedin_url: Optional[str]
    company_name: Optional[str]
    company_domain: Optional[str]
    title: Optional[str]
    industry: Optional[str]

    # Intelligence
    intent_score: float
    confidence: float
    icp_match_score: float
    technographics: list
    hiring_signals: list
    recent_news: list
    communication_style: Optional[str]

    # Status
    status: str
    sentiment: Optional[str]
    source: Optional[str]
    tags: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    leads: list[LeadResponse]


class LeadDetailResponse(LeadResponse):
    """Extended response with all intelligence data."""
    phone: Optional[str]
    photo_url: Optional[str]
    company_size: Optional[str]
    company_location: Optional[str]
    last_4_posts: list
    website_changes: list
    social_engagement: list
    content_intent: list
    hobbies: list
    common_ground: list
    media_quotes: list
    review_highlights: list
    objection_type: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class BuyingCommitteeMember(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    personalization_angle: Optional[str] = None
    communication_style: str = "formal"


class BuyingCommitteeResponse(BaseModel):
    id: int
    lead_id: int
    name: str
    role: Optional[str]
    email: Optional[str]
    personalization_angle: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class HuntRequest(BaseModel):
    """POST /api/v1/hunt/start - Start the AI hunt process."""
    campaign_id: Optional[int] = None
    target_domains: list[str] = []
    target_linkedin_urls: list[str] = []
    icp_description: Optional[str] = None
    lookalike_company: Optional[str] = None
    max_leads: int = 100
    signals_to_track: list[str] = [
        "technographics", "hiring_intent", "news",
        "website_changes", "social_engagement", "content_intent"
    ]
    auto_personalize: bool = True
    auto_score: bool = True


class HuntResponse(BaseModel):
    hunt_id: str
    status: str
    message: str
    estimated_leads: int
