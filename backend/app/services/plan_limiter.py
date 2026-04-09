"""
HUNTER.OS - Plan Limiter Service
Enforces trial/pro/enterprise usage limits.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User

logger = logging.getLogger(__name__)

# Plan limits configuration
PLAN_LIMITS = {
    "trial": {
        "leads_per_month": 10,
        "messages_per_month": 5,
        "footprint_scans_per_month": 5,
        "products": 1,
        "linkedin_automation": False,
        "email_sending": False,
        "analytics_level": "basic",
        "team_members": 1,
        "api_access": False,
        "trial_days": 14,
        # ADDED (Phase 11): cost-optimised provider quotas
        "serp_queries_per_month": 50,
        "enrichment_calls_per_month": 20,
    },
    "pro": {
        "leads_per_month": -1,  # unlimited
        "messages_per_month": -1,
        "footprint_scans_per_month": -1,
        "products": 3,
        "linkedin_automation": True,
        "email_sending": True,
        "analytics_level": "detailed",
        "team_members": 3,
        "api_access": False,
        "trial_days": 0,
        # ADDED (Phase 11)
        "serp_queries_per_month": 5000,
        "enrichment_calls_per_month": 500,
    },
    "enterprise": {
        "leads_per_month": -1,
        "messages_per_month": -1,
        "footprint_scans_per_month": -1,
        "bulk_footprint_scan": True,
        "products": -1,
        "linkedin_automation": True,
        "email_sending": True,
        "analytics_level": "full",
        "team_members": 10,
        "api_access": True,
        "trial_days": 0,
        # ADDED (Phase 11): unlimited
        "serp_queries_per_month": -1,
        "enrichment_calls_per_month": -1,
    },
}


class PlanLimiter:
    """Checks and enforces plan-based usage limits."""

    def __init__(self, db: Session):
        self.db = db

    def check_limit(self, user: User, action: str, count: int = 1) -> dict:
        """
        Check if user can perform an action based on their plan.
        Returns: {"allowed": bool, "remaining": int, "limit": int, "plan": str}
        """
        plan = getattr(user, "plan", "trial") or "trial"
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])
        usage = self._get_usage(user)

        # Check trial expiration
        if plan == "trial":
            trial_end = getattr(user, "trial_ends_at", None)
            if trial_end:
                try:
                    if trial_end.tzinfo is None:
                        trial_end = trial_end.replace(tzinfo=timezone.utc)
                except Exception:
                    trial_end = None
            if trial_end and datetime.now(timezone.utc) > trial_end:
                return {
                    "allowed": False,
                    "reason": "trial_expired",
                    "message": "Deneme süreniz doldu. Pro plana geçerek sınırsız kullanıma erişin!",
                    "plan": plan,
                }

        # Check specific limits
        if action == "discover_leads":
            limit = limits["leads_per_month"]
            current = usage.get("leads_discovered", 0)
        elif action == "send_message":
            limit = limits["messages_per_month"]
            current = usage.get("messages_sent", 0)
        elif action == "create_product":
            limit = limits["products"]
            current = usage.get("products_count", 0)
        elif action == "footprint_scan":
            limit = limits.get("footprint_scans_per_month", 5)
            current = usage.get("footprint_scans", 0)
        # ADDED (Phase 11): SERP query budget
        elif action == "serp_query":
            limit = limits.get("serp_queries_per_month", 50)
            current = usage.get("serp_queries", 0)
        # ADDED (Phase 11): paid enrichment call budget
        elif action == "enrichment_call":
            limit = limits.get("enrichment_calls_per_month", 20)
            current = usage.get("enrichment_calls", 0)
        elif action == "linkedin_action":
            if not limits["linkedin_automation"]:
                return {
                    "allowed": False,
                    "reason": "feature_locked",
                    "message": "LinkedIn otomasyonu Pro planda kullanılabilir.",
                    "plan": plan,
                }
            return {"allowed": True, "plan": plan}
        elif action == "send_email":
            if not limits["email_sending"]:
                return {
                    "allowed": False,
                    "reason": "feature_locked",
                    "message": "Email gönderimi Pro planda kullanılabilir.",
                    "plan": plan,
                }
            return {"allowed": True, "plan": plan}
        else:
            return {"allowed": True, "plan": plan}

        # Unlimited check
        if limit == -1:
            return {"allowed": True, "remaining": -1, "limit": -1, "plan": plan}

        remaining = max(0, limit - current)
        allowed = current + count <= limit

        if not allowed:
            return {
                "allowed": False,
                "remaining": remaining,
                "limit": limit,
                "current": current,
                "reason": "limit_reached",
                "message": f"Aylık {action} limitinize ulaştınız ({current}/{limit}). Pro plana geçerek sınırsız kullanıma erişin!",
                "plan": plan,
            }

        return {"allowed": True, "remaining": remaining - count, "limit": limit, "plan": plan}

    def increment_usage(self, user: User, action: str, count: int = 1):
        """Increment usage counter for an action."""
        usage = dict(self._get_usage(user))  # Copy to trigger SQLAlchemy change detection

        if action == "discover_leads":
            usage["leads_discovered"] = usage.get("leads_discovered", 0) + count
        elif action == "send_message":
            usage["messages_sent"] = usage.get("messages_sent", 0) + count
        elif action == "create_product":
            usage["products_count"] = usage.get("products_count", 0) + count
        elif action == "footprint_scan":
            usage["footprint_scans"] = usage.get("footprint_scans", 0) + count
        # ADDED (Phase 11)
        elif action == "serp_query":
            usage["serp_queries"] = usage.get("serp_queries", 0) + count
        elif action == "enrichment_call":
            usage["enrichment_calls"] = usage.get("enrichment_calls", 0) + count

        user.usage_this_month = usage  # Reassign to mark column as dirty
        self.db.commit()

    def get_usage_summary(self, user: User) -> dict:
        """Get current usage summary for the user."""
        plan = getattr(user, "plan", "trial") or "trial"
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])
        usage = self._get_usage(user)

        trial_info = {}
        if plan == "trial":
            trial_end = getattr(user, "trial_ends_at", None)
            if trial_end:
                try:
                    # Handle both naive and aware datetimes
                    if trial_end.tzinfo is None:
                        trial_end = trial_end.replace(tzinfo=timezone.utc)
                    days_left = max(0, (trial_end - datetime.now(timezone.utc)).days)
                    trial_info = {
                        "trial_ends_at": str(trial_end),
                        "days_remaining": days_left,
                        "is_expired": days_left <= 0,
                    }
                except Exception:
                    trial_info = {"days_remaining": 14, "is_expired": False}
            else:
                trial_info = {"days_remaining": 14, "is_expired": False}

        return {
            "plan": plan,
            "usage": usage,
            "limits": limits,
            "trial": trial_info,
        }

    def check_footprint_scan(self, user: User):
        """Guard for footprint scan endpoints. Raises HTTP 402 if limit exceeded."""
        self.require_limit(user, "footprint_scan")
        self.increment_usage(user, "footprint_scan")

    def require_limit(self, user: User, action: str, count: int = 1):
        """Check limit and raise HTTP 402 if exceeded. Use as guard in endpoints."""
        result = self.check_limit(user, action, count)
        if not result["allowed"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "plan_limit_exceeded",
                    "reason": result.get("reason"),
                    "message": result.get("message"),
                    "plan": result.get("plan"),
                    "upgrade_url": "/pricing",
                },
            )

    @staticmethod
    def _get_usage(user: User) -> dict:
        """Get current month's usage data."""
        usage = getattr(user, "usage_this_month", None) or {}
        if isinstance(usage, str):
            import json
            usage = json.loads(usage)
        return usage
