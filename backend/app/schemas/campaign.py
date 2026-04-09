"""
HUNTER.OS - Campaign & Workflow Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WorkflowStep(BaseModel):
    step: int
    channel: str                # linkedin_visit | email | linkedin_connect | linkedin_dm
    delay_hours: int = 0
    template_id: Optional[str] = None
    condition: Optional[dict] = None  # {"if": "email_opened", "then": "proceed", "else": "skip_to_step_X"}


class ABVariant(BaseModel):
    variant_id: str
    template: str
    weight: float = 0.5        # 50% by default


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icp_criteria: dict = {}
    workflow_steps: list[WorkflowStep] = []
    ab_variants: list[ABVariant] = []
    tags: list[str] = []


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    workflow_steps: Optional[list[WorkflowStep]] = None
    ab_variants: Optional[list[ABVariant]] = None
    tags: Optional[list[str]] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    total_leads: int
    total_contacted: int
    total_replied: int
    total_meetings: int
    reply_rate: float
    meeting_rate: float
    workflow_steps: list
    ab_variants: list
    winning_variant: Optional[str]
    tags: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    total: int
    campaigns: list[CampaignResponse]


class CampaignAutopsyResponse(BaseModel):
    """AI-generated campaign performance analysis."""
    campaign_id: int
    campaign_name: str
    summary: str                        # AI narrative
    best_variant: Optional[str]
    best_channel: Optional[str]
    best_day: Optional[str]
    best_hour: Optional[int]
    top_signal: Optional[str]           # Which signal drove most replies
    reply_rate: float
    meeting_rate: float
    total_revenue_attributed: float
    recommendations: list[str]          # AI suggestions for next campaign
