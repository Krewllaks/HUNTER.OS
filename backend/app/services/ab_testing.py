"""
HUNTER.OS - A/B Testing Engine
Statistical variant comparison for campaigns.
Supports message variants, subject lines, send times, channels.
"""
import logging
import math
import random
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.campaign import Campaign, Workflow, CampaignAnalytics

logger = logging.getLogger(__name__)


class ABTestingEngine:
    """
    Manages A/B testing for campaigns:
    - Assigns variants to leads
    - Tracks per-variant metrics
    - Determines statistical significance
    - Auto-selects winners
    """

    def __init__(self, db: Session):
        self.db = db

    def assign_variant(self, campaign: Campaign, lead_id: int) -> Optional[str]:
        """Assign a variant to a lead for A/B testing."""
        variants = campaign.ab_variants or []
        if not variants or len(variants) < 2:
            return None

        # If winner already declared, use winning variant
        if campaign.winning_variant:
            return campaign.winning_variant

        # Weighted random assignment based on variant weights
        variant_names = [v.get("name", f"Variant {i}") for i, v in enumerate(variants)]
        weights = [v.get("weight", 1.0) for v in variants]
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        chosen = random.choices(variant_names, weights=weights, k=1)[0]
        return chosen

    def record_event(
        self,
        campaign_id: int,
        variant: str,
        channel: str,
        event_type: str,
    ):
        """Record an A/B test event (sent, opened, clicked, replied, meeting)."""
        today = datetime.now(timezone.utc).date()

        # Find or create analytics record for today
        record = (
            self.db.query(CampaignAnalytics)
            .filter(
                and_(
                    CampaignAnalytics.campaign_id == campaign_id,
                    CampaignAnalytics.date == today,
                    CampaignAnalytics.variant == variant,
                    CampaignAnalytics.channel == channel,
                )
            )
            .first()
        )

        if not record:
            record = CampaignAnalytics(
                campaign_id=campaign_id,
                date=today,
                variant=variant,
                channel=channel,
            )
            self.db.add(record)
            self.db.flush()

        # Increment the appropriate counter
        if event_type == "sent":
            record.sent = (record.sent or 0) + 1
        elif event_type == "opened":
            record.opened = (record.opened or 0) + 1
        elif event_type == "clicked":
            record.clicked = (record.clicked or 0) + 1
        elif event_type == "replied":
            record.replied = (record.replied or 0) + 1
        elif event_type == "positive_reply":
            record.positive_replies = (record.positive_replies or 0) + 1
        elif event_type == "meeting":
            record.meetings_booked = (record.meetings_booked or 0) + 1

        self.db.commit()

    def get_variant_stats(self, campaign_id: int) -> dict:
        """Get aggregated stats per variant for a campaign."""
        results = (
            self.db.query(
                CampaignAnalytics.variant,
                func.sum(CampaignAnalytics.sent).label("total_sent"),
                func.sum(CampaignAnalytics.opened).label("total_opened"),
                func.sum(CampaignAnalytics.clicked).label("total_clicked"),
                func.sum(CampaignAnalytics.replied).label("total_replied"),
                func.sum(CampaignAnalytics.positive_replies).label("total_positive"),
                func.sum(CampaignAnalytics.meetings_booked).label("total_meetings"),
            )
            .filter(CampaignAnalytics.campaign_id == campaign_id)
            .group_by(CampaignAnalytics.variant)
            .all()
        )

        stats = {}
        for row in results:
            sent = row.total_sent or 0
            stats[row.variant] = {
                "sent": sent,
                "opened": row.total_opened or 0,
                "clicked": row.total_clicked or 0,
                "replied": row.total_replied or 0,
                "positive_replies": row.total_positive or 0,
                "meetings": row.total_meetings or 0,
                "open_rate": (row.total_opened or 0) / max(sent, 1) * 100,
                "reply_rate": (row.total_replied or 0) / max(sent, 1) * 100,
                "meeting_rate": (row.total_meetings or 0) / max(row.total_replied or 0, 1) * 100,
            }

        return stats

    def check_significance(self, campaign_id: int, min_samples: int = 50) -> dict:
        """
        Check if there's a statistically significant winner.
        Uses Z-test for proportions (reply rate comparison).
        """
        stats = self.get_variant_stats(campaign_id)

        if len(stats) < 2:
            return {"significant": False, "reason": "Need at least 2 variants"}

        variants = list(stats.items())
        best_variant = None
        best_rate = -1
        is_significant = False

        for name, data in variants:
            if data["sent"] < min_samples:
                return {
                    "significant": False,
                    "reason": f"Need at least {min_samples} sends per variant. "
                              f"{name} has {data['sent']}.",
                    "stats": stats,
                }

            if data["reply_rate"] > best_rate:
                best_rate = data["reply_rate"]
                best_variant = name

        # Z-test between best and second-best
        sorted_variants = sorted(variants, key=lambda x: x[1]["reply_rate"], reverse=True)
        if len(sorted_variants) >= 2:
            a_name, a_data = sorted_variants[0]
            b_name, b_data = sorted_variants[1]

            p1 = a_data["replied"] / max(a_data["sent"], 1)
            p2 = b_data["replied"] / max(b_data["sent"], 1)
            n1 = a_data["sent"]
            n2 = b_data["sent"]

            # Pooled proportion
            p_pool = (a_data["replied"] + b_data["replied"]) / max(n1 + n2, 1)

            if p_pool > 0 and p_pool < 1:
                se = math.sqrt(p_pool * (1 - p_pool) * (1 / max(n1, 1) + 1 / max(n2, 1)))
                if se > 0:
                    z_score = (p1 - p2) / se
                    # 95% confidence = z > 1.96
                    is_significant = abs(z_score) > 1.96
                    confidence = min(99.9, abs(z_score) / 1.96 * 95)

                    return {
                        "significant": is_significant,
                        "winner": best_variant if is_significant else None,
                        "z_score": round(z_score, 3),
                        "confidence": round(confidence, 1),
                        "stats": stats,
                    }

        return {
            "significant": False,
            "reason": "Insufficient data for significance test",
            "stats": stats,
        }

    def auto_select_winner(self, campaign_id: int, min_samples: int = 50) -> Optional[str]:
        """
        Automatically select the winning variant if statistically significant.
        Updates the campaign record.
        """
        result = self.check_significance(campaign_id, min_samples)

        if result.get("significant") and result.get("winner"):
            campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign and not campaign.winning_variant:
                campaign.winning_variant = result["winner"]
                self.db.commit()
                logger.info(
                    f"Campaign {campaign_id}: Winner auto-selected = {result['winner']} "
                    f"(z={result['z_score']}, confidence={result['confidence']}%)"
                )
                return result["winner"]

        return None
