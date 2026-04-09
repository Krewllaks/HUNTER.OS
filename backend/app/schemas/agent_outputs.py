"""
HUNTER.OS - Pydantic validation schemas for AI agent outputs.
Prevents hallucinated/malformed agent responses from corrupting the database.

Each schema maps to a specific agent's expected JSON output structure.
Use validate_agent_output() from base_agent.py to parse raw LLM responses.
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# ProductAnalysisAgent output
# ---------------------------------------------------------------------------

class ValueProposition(BaseModel):
    """Nested schema for product value proposition."""
    summary: str = Field(default="")
    core_benefit: str = Field(default="")
    differentiators: list[str] = Field(default_factory=list)


class TargetMarket(BaseModel):
    """Nested schema for target market segment."""
    primary_segments: list[str] = Field(default_factory=list)
    market_size_estimate: str = Field(default="Medium")
    urgency_level: str = Field(default="Medium")


class ICPProfile(BaseModel):
    """Nested schema for ideal customer profile."""
    industries: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)


class SearchStrategies(BaseModel):
    """Nested schema for search/discovery strategies."""
    linkedin_queries: list[str] = Field(default_factory=list)
    google_queries: list[str] = Field(default_factory=list)
    content_topics: list[str] = Field(default_factory=list)
    competitor_products: list[str] = Field(default_factory=list)
    communities: list[str] = Field(default_factory=list)


class OutreachAngles(BaseModel):
    """Nested schema for outreach messaging angles."""
    primary_hook: str = Field(default="")
    follow_up_angles: list[str] = Field(default_factory=list)
    objection_preempts: list[str] = Field(default_factory=list)


class ICPAnalysis(BaseModel):
    """Output schema for ProductAnalysisAgent.analyze()."""
    value_proposition: ValueProposition = Field(default_factory=ValueProposition)
    target_market: TargetMarket = Field(default_factory=TargetMarket)
    icp_profile: ICPProfile = Field(default_factory=ICPProfile)
    search_strategies: SearchStrategies = Field(default_factory=SearchStrategies)
    outreach_angles: OutreachAngles = Field(default_factory=OutreachAngles)


# ---------------------------------------------------------------------------
# ResearchAgent output (ReAct FINISH answer)
# ---------------------------------------------------------------------------

class LeadResearchResult(BaseModel):
    """Output schema for ResearchAgent's final intelligence dossier."""
    technographics: Optional[dict] = None
    hiring_signals: Optional[dict] = None
    news_funding: Optional[dict] = None
    website_changes: Optional[dict] = None
    content_intent: Optional[dict] = None
    social_engagement: Optional[dict] = None
    competitive_displacement: Optional[dict] = None
    overall_summary: str = Field(default="")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        """Clamp confidence to [0, 1] range instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


# ---------------------------------------------------------------------------
# ScoringAgent output
# ---------------------------------------------------------------------------

class LeadScore(BaseModel):
    """Output schema for ScoringAgent.score_lead()."""
    chain_of_thought: str = Field(default="")
    icp_match_score: int = Field(default=0, ge=0, le=100)
    intent_score: int = Field(default=0, ge=0, le=100)
    accessibility_score: int = Field(default=0, ge=0, le=100)
    timing_score: int = Field(default=0, ge=0, le=100)
    final_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: int = Field(default=50, ge=0, le=100)
    top_signals: list[str] = Field(default_factory=list)
    recommended_approach: str = Field(default="")
    urgency: str = Field(default="medium")

    @field_validator("icp_match_score", "intent_score", "accessibility_score",
                     "timing_score", "confidence", mode="before")
    @classmethod
    def clamp_int_score(cls, v):
        """Clamp integer scores to [0, 100] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0, min(100, int(v)))
        return v

    @field_validator("final_score", mode="before")
    @classmethod
    def clamp_final_score(cls, v):
        """Clamp final_score to [0, 100] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(100.0, float(v)))
        return v


# ---------------------------------------------------------------------------
# PersonalizationAgent output
# ---------------------------------------------------------------------------

class PersonalizedMessage(BaseModel):
    """Output schema for PersonalizationAgent.generate_message()."""
    subject_line: str = Field(default="")
    body: str = Field(default="")
    ps_note: str = Field(default="")
    personalization_signals_used: list[str] = Field(default_factory=list)
    tone: str = Field(default="professional")
    estimated_reply_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    alternative_subject: str = Field(default="")
    channel: str = Field(default="email")

    @field_validator("estimated_reply_probability", mode="before")
    @classmethod
    def clamp_reply_prob(cls, v):
        """Clamp probability to [0, 1] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


class ObjectionResponse(BaseModel):
    """Output schema for PersonalizationAgent.generate_objection_response()."""
    response: str = Field(default="")
    strategy_used: str = Field(default="")
    tone: str = Field(default="empathetic")
    next_step_suggestion: str = Field(default="")


class FollowUpMessage(BaseModel):
    """Output schema for PersonalizationAgent.generate_follow_up()."""
    subject_line: str = Field(default="")
    body: str = Field(default="")
    ps_note: str = Field(default="")
    personalization_signals_used: list[str] = Field(default_factory=list)
    tone: str = Field(default="professional")
    estimated_reply_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    alternative_subject: str = Field(default="")
    channel: str = Field(default="email")
    follow_up_number: int = Field(default=1, ge=1)

    @field_validator("estimated_reply_probability", mode="before")
    @classmethod
    def clamp_reply_prob(cls, v):
        """Clamp probability to [0, 1] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


# ---------------------------------------------------------------------------
# SentimentService output
# ---------------------------------------------------------------------------

class SentimentAnalysis(BaseModel):
    """Output schema for SentimentService reply classification."""
    sentiment: str = Field(default="neutral")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    intent: str = Field(default="other")
    summary: str = Field(default="")
    should_stop_automation: bool = Field(default=True)
    suggested_action: str = Field(default="escalate")
    urgency: str = Field(default="medium")

    @field_validator("sentiment", mode="before")
    @classmethod
    def validate_sentiment(cls, v):
        """Normalize sentiment to allowed values."""
        allowed = {"positive", "negative", "neutral", "objection"}
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "neutral"

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        """Clamp confidence to [0, 1] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v

    @field_validator("urgency", mode="before")
    @classmethod
    def validate_urgency(cls, v):
        """Normalize urgency to allowed values."""
        allowed = {"high", "medium", "low"}
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "medium"

    @field_validator("intent", mode="before")
    @classmethod
    def validate_intent(cls, v):
        """Normalize intent to allowed values."""
        allowed = {
            "meeting_request", "price_inquiry", "not_interested",
            "info_request", "referral", "out_of_office", "auto_reply", "other",
        }
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "other"

    @field_validator("suggested_action", mode="before")
    @classmethod
    def validate_action(cls, v):
        """Normalize suggested_action to allowed values."""
        allowed = {
            "schedule_meeting", "send_info", "handle_objection",
            "mark_lost", "wait", "escalate",
        }
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "escalate"


# ---------------------------------------------------------------------------
# ContentAnalystAgent output
# ---------------------------------------------------------------------------

class QuotableMoment(BaseModel):
    """A quotable moment from a lead's content."""
    source: str = Field(default="")
    quote: str = Field(default="")
    context: str = Field(default="")


class BestApproach(BaseModel):
    """Recommended approach for reaching a lead."""
    opening_angle: str = Field(default="")
    tone_to_use: str = Field(default="")
    topics_to_reference: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class ContentAnalysis(BaseModel):
    """Output schema for ContentAnalystAgent.analyze()."""
    communication_style: str = Field(default="formal")
    topics: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    interests_hobbies: list[str] = Field(default_factory=list)
    tone: str = Field(default="neutral")
    recent_focus: str = Field(default="")
    personality_type: str = Field(default="analytical")
    quotable_moments: list[QuotableMoment] = Field(default_factory=list)
    engagement_style: str = Field(default="unknown")
    best_approach: BestApproach = Field(default_factory=BestApproach)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        """Clamp confidence to [0, 1] instead of rejecting."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v

    @field_validator("communication_style", mode="before")
    @classmethod
    def validate_style(cls, v):
        """Normalize communication style."""
        allowed = {"formal", "casual", "mixed", "academic", "storytelling"}
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "formal"

    @field_validator("personality_type", mode="before")
    @classmethod
    def validate_personality(cls, v):
        """Normalize personality type."""
        allowed = {"analytical", "driver", "expressive", "amiable"}
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in allowed:
                return normalized
        return "analytical"
