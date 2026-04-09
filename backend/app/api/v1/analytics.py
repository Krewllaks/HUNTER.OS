"""
HUNTER.OS - Analytics & ROI Tracking API
Campaign autopsy, revenue attribution, performance metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.models.campaign import Campaign, CampaignAnalytics
from app.models.message import Message

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def get_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Main analytics dashboard data:
    - Total leads, contacted, replied, meetings
    - Reply rate, meeting rate
    - Revenue attributed
    - Top performing signals
    - Channel performance
    """
    total_leads = db.query(Lead).filter(Lead.user_id == current_user.id).count()
    contacted = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.status.in_(["contacted", "replied", "meeting", "won"]),
    ).count()
    replied = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.status.in_(["replied", "meeting", "won"]),
    ).count()
    meetings = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.status.in_(["meeting", "won"]),
    ).count()
    won = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.status == "won",
    ).count()

    # Messages stats
    total_outbound = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.direction == "outbound",
    ).count()
    total_inbound = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.direction == "inbound",
    ).count()

    # Campaign stats
    active_campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id,
        Campaign.status == "active",
    ).count()

    # Revenue attribution
    total_revenue = db.query(func.sum(CampaignAnalytics.revenue_attributed)).join(
        Campaign
    ).filter(Campaign.user_id == current_user.id).scalar() or 0

    # Sentiment distribution
    positive = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.sentiment == "positive",
    ).count()
    negative = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.sentiment == "negative",
    ).count()
    neutral = db.query(Lead).filter(
        Lead.user_id == current_user.id,
        Lead.sentiment == "neutral",
    ).count()

    reply_rate = (replied / max(contacted, 1)) * 100
    meeting_rate = (meetings / max(replied, 1)) * 100
    win_rate = (won / max(meetings, 1)) * 100

    return {
        "overview": {
            "total_leads": total_leads,
            "contacted": contacted,
            "replied": replied,
            "meetings": meetings,
            "won": won,
            "reply_rate": round(reply_rate, 1),
            "meeting_rate": round(meeting_rate, 1),
            "win_rate": round(win_rate, 1),
        },
        "messages": {
            "total_outbound": total_outbound,
            "total_inbound": total_inbound,
        },
        "campaigns": {
            "active": active_campaigns,
        },
        "revenue": {
            "total_attributed": total_revenue,
        },
        "sentiment": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
        },
    }


@router.get("/campaigns/{campaign_id}/autopsy")
def get_campaign_autopsy(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Campaign Autopsy: AI-analyzed performance breakdown.
    Shows what worked, what didn't, and recommendations.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Gather analytics
    analytics = db.query(CampaignAnalytics).filter(
        CampaignAnalytics.campaign_id == campaign_id,
    ).all()

    # Calculate per-variant performance
    variant_performance = {}
    for a in analytics:
        v = a.variant or "default"
        if v not in variant_performance:
            variant_performance[v] = {
                "sent": 0, "opened": 0, "replied": 0,
                "meetings": 0, "revenue": 0,
            }
        variant_performance[v]["sent"] += a.sent
        variant_performance[v]["opened"] += a.opened
        variant_performance[v]["replied"] += a.replied
        variant_performance[v]["meetings"] += a.meetings_booked
        variant_performance[v]["revenue"] += a.revenue_attributed

    # Find best variant
    best_variant = max(
        variant_performance.items(),
        key=lambda x: x[1]["replied"] / max(x[1]["sent"], 1),
        default=(None, {}),
    )

    # Channel breakdown
    channel_stats = {}
    for a in analytics:
        ch = a.channel or "email"
        if ch not in channel_stats:
            channel_stats[ch] = {"sent": 0, "replied": 0}
        channel_stats[ch]["sent"] += a.sent
        channel_stats[ch]["replied"] += a.replied

    best_channel = max(
        channel_stats.items(),
        key=lambda x: x[1]["replied"] / max(x[1]["sent"], 1),
        default=(None, {}),
    )

    # Generate recommendations
    recommendations = []
    if campaign.reply_rate and campaign.reply_rate < 5:
        recommendations.append("Reply rate is below 5%. Consider revising message personalization or targeting criteria.")
    if best_variant[0] and best_variant[0] != "default":
        recommendations.append(f"Variant '{best_variant[0]}' outperformed others. Consider using it as the default.")
    if campaign.total_meetings and campaign.total_contacted:
        if (campaign.total_meetings / campaign.total_contacted * 100) < 2:
            recommendations.append("Meeting conversion is low. Add a Calendly/scheduling link to reduce friction.")

    total_revenue = sum(v["revenue"] for v in variant_performance.values())

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "summary": {
            "total_leads": campaign.total_leads,
            "total_contacted": campaign.total_contacted,
            "total_replied": campaign.total_replied,
            "total_meetings": campaign.total_meetings,
            "reply_rate": campaign.reply_rate,
            "meeting_rate": campaign.meeting_rate,
        },
        "best_variant": best_variant[0],
        "best_channel": best_channel[0] if best_channel else None,
        "variant_breakdown": variant_performance,
        "channel_breakdown": channel_stats,
        "total_revenue_attributed": total_revenue,
        "recommendations": recommendations,
        "winning_variant": campaign.winning_variant,
    }


@router.get("/leads/scoring-distribution")
def get_scoring_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lead scoring distribution for visualization."""
    leads = db.query(
        Lead.intent_score, Lead.confidence, Lead.icp_match_score, Lead.status
    ).filter(Lead.user_id == current_user.id).all()

    # Bucket scores
    buckets = {"hot": 0, "warm": 0, "cool": 0, "cold": 0}
    for lead in leads:
        score = lead.intent_score or 0
        if score >= 75:
            buckets["hot"] += 1
        elif score >= 50:
            buckets["warm"] += 1
        elif score >= 25:
            buckets["cool"] += 1
        else:
            buckets["cold"] += 1

    return {
        "total": len(leads),
        "distribution": buckets,
        "avg_score": sum(l.intent_score or 0 for l in leads) / max(len(leads), 1),
        "avg_confidence": sum(l.confidence or 0 for l in leads) / max(len(leads), 1),
    }
