"""
HUNTER.OS - LLM Budget Guard
Pre-call check that raises HTTP 402 when a user's monthly LLM token budget is exhausted.
"""
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.llm_cost_tracker import llm_cost_tracker
from app.core.config import settings

logger = logging.getLogger(__name__)


def check_llm_budget(user_id: int, plan: str, db: Session) -> None:
    """
    Verify the user still has LLM token budget remaining.

    Raises:
        HTTPException 402 if the monthly budget is exceeded.
    Logs:
        Warning when usage crosses the alert threshold (default 80%).
    """
    result = llm_cost_tracker.check_budget(db, user_id, plan)

    if result["pct"] >= settings.LLM_COST_ALERT_THRESHOLD and result["allowed"]:
        logger.warning(
            f"LLM budget warning: user={user_id} plan={plan} "
            f"usage={result['usage']}/{result['budget']} ({result['pct']:.0%})"
        )

    if not result["allowed"]:
        logger.warning(
            f"LLM budget exceeded: user={user_id} plan={plan} "
            f"usage={result['usage']}/{result['budget']}"
        )
        raise HTTPException(
            status_code=402,
            detail="Monthly LLM token budget exceeded. Upgrade your plan.",
        )
