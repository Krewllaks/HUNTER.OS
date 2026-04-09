"""
HUNTER.OS - LLM Cost Tracker
Tracks token usage per user, per agent. Stores in User.usage_this_month JSON field.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Budget mapping: plan name -> monthly token limit
_PLAN_BUDGETS = {
    "trial": settings.LLM_MONTHLY_TOKEN_BUDGET_TRIAL,
    "pro": settings.LLM_MONTHLY_TOKEN_BUDGET_PRO,
    "enterprise": settings.LLM_MONTHLY_TOKEN_BUDGET_ENTERPRISE,
}


class LLMCostTracker:
    """
    Records and queries LLM token usage stored in User.usage_this_month.

    Schema inside usage_this_month:
    {
        "leads_discovered": ...,
        "messages_sent": ...,
        "llm_tokens": {
            "total_input": 0,
            "total_output": 0,
            "total": 0,
            "by_agent": {
                "ProductAnalysisAgent": {"input": 0, "output": 0, "calls": 0},
                ...
            },
            "last_recorded_at": "2026-03-25T12:00:00Z"
        }
    }
    """

    @staticmethod
    def _ensure_llm_tokens(usage: dict) -> dict:
        """Ensure the llm_tokens sub-structure exists."""
        if "llm_tokens" not in usage:
            usage["llm_tokens"] = {
                "total_input": 0,
                "total_output": 0,
                "total": 0,
                "by_agent": {},
                "last_recorded_at": None,
            }
        return usage["llm_tokens"]

    def record_usage(
        self,
        db: Session,
        user_id: int,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """
        Record token consumption for a specific user and agent.
        Updates the User.usage_this_month JSON field atomically.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"LLMCostTracker: user {user_id} not found, skipping record")
            return

        usage = dict(user.usage_this_month or {})
        llm = self._ensure_llm_tokens(usage)

        # Update totals
        llm["total_input"] = llm.get("total_input", 0) + input_tokens
        llm["total_output"] = llm.get("total_output", 0) + output_tokens
        llm["total"] = llm.get("total", 0) + input_tokens + output_tokens
        llm["last_recorded_at"] = datetime.now(timezone.utc).isoformat()

        # Update per-agent breakdown
        by_agent = llm.setdefault("by_agent", {})
        agent_stats = by_agent.setdefault(agent_name, {"input": 0, "output": 0, "calls": 0})
        agent_stats["input"] = agent_stats.get("input", 0) + input_tokens
        agent_stats["output"] = agent_stats.get("output", 0) + output_tokens
        agent_stats["calls"] = agent_stats.get("calls", 0) + 1

        usage["llm_tokens"] = llm
        user.usage_this_month = usage
        db.commit()

        total = llm["total"]
        logger.debug(
            f"LLM usage recorded: user={user_id} agent={agent_name} "
            f"+{input_tokens}in +{output_tokens}out total={total}"
        )

        # Check alert threshold
        budget = _PLAN_BUDGETS.get(user.plan, _PLAN_BUDGETS["trial"])
        pct = total / budget if budget > 0 else 1.0
        if pct >= settings.LLM_COST_ALERT_THRESHOLD:
            logger.warning(
                f"LLM budget alert: user={user_id} plan={user.plan} "
                f"usage={total}/{budget} ({pct:.0%})"
            )

    def check_budget(self, db: Session, user_id: int, plan: str) -> dict:
        """
        Check whether a user is within their LLM token budget.

        Returns:
            {"allowed": bool, "usage": int, "budget": int, "pct": float}
        """
        budget = _PLAN_BUDGETS.get(plan, _PLAN_BUDGETS["trial"])

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"allowed": False, "usage": 0, "budget": budget, "pct": 0.0}

        usage = dict(user.usage_this_month or {})
        llm = usage.get("llm_tokens", {})
        total = llm.get("total", 0)
        pct = total / budget if budget > 0 else 1.0

        return {
            "allowed": total < budget,
            "usage": total,
            "budget": budget,
            "pct": round(pct, 4),
        }

    def get_usage_stats(self, db: Session, user_id: int) -> dict:
        """
        Return full LLM usage breakdown for a user.

        Returns:
            {
                "total_input": int,
                "total_output": int,
                "total": int,
                "by_agent": {agent_name: {input, output, calls}, ...},
                "budget": int,
                "pct": float,
                "plan": str,
            }
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"total_input": 0, "total_output": 0, "total": 0, "by_agent": {}}

        usage = dict(user.usage_this_month or {})
        llm = usage.get("llm_tokens", {})
        budget = _PLAN_BUDGETS.get(user.plan, _PLAN_BUDGETS["trial"])
        total = llm.get("total", 0)

        return {
            "total_input": llm.get("total_input", 0),
            "total_output": llm.get("total_output", 0),
            "total": total,
            "by_agent": llm.get("by_agent", {}),
            "budget": budget,
            "pct": round(total / budget, 4) if budget > 0 else 1.0,
            "plan": user.plan,
            "last_recorded_at": llm.get("last_recorded_at"),
        }


# Singleton for convenience
llm_cost_tracker = LLMCostTracker()
