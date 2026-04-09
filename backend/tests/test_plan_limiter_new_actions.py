"""
Phase 11 — PlanLimiter new action tests.

Verifies the new ``serp_query`` and ``enrichment_call`` actions
respect per-plan quotas. PlanLimiter is exercised with a fake
in-memory User and a stub DB session — no SQLAlchemy traffic.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.plan_limiter import PlanLimiter, PLAN_LIMITS


def _make_user(plan: str, usage: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        plan=plan,
        usage_this_month=usage or {},
        trial_ends_at=None,
    )


def _make_limiter() -> PlanLimiter:
    return PlanLimiter(db=MagicMock(name="FakeSession"))


# ─────────────────────────────────────────────────────
# PLAN_LIMITS dict has the new keys for every plan
# ─────────────────────────────────────────────────────
class TestPlanLimitsDict:
    def test_trial_has_serp_quota(self):
        assert PLAN_LIMITS["trial"]["serp_queries_per_month"] == 50
        assert PLAN_LIMITS["trial"]["enrichment_calls_per_month"] == 20

    def test_pro_has_serp_quota(self):
        assert PLAN_LIMITS["pro"]["serp_queries_per_month"] == 5000
        assert PLAN_LIMITS["pro"]["enrichment_calls_per_month"] == 500

    def test_enterprise_unlimited(self):
        assert PLAN_LIMITS["enterprise"]["serp_queries_per_month"] == -1
        assert PLAN_LIMITS["enterprise"]["enrichment_calls_per_month"] == -1


# ─────────────────────────────────────────────────────
# Trial enforcement
# ─────────────────────────────────────────────────────
class TestTrialLimits:
    def test_trial_serp_under_limit(self):
        user = _make_user("trial", {"serp_queries": 49})
        result = _make_limiter().check_limit(user, "serp_query")
        assert result["allowed"] is True

    def test_trial_serp_at_limit_blocked(self):
        user = _make_user("trial", {"serp_queries": 50})
        result = _make_limiter().check_limit(user, "serp_query")
        assert result["allowed"] is False
        assert result["reason"] == "limit_reached"

    def test_trial_enrichment_under_limit(self):
        user = _make_user("trial", {"enrichment_calls": 19})
        result = _make_limiter().check_limit(user, "enrichment_call")
        assert result["allowed"] is True

    def test_trial_enrichment_at_limit_blocked(self):
        user = _make_user("trial", {"enrichment_calls": 20})
        result = _make_limiter().check_limit(user, "enrichment_call")
        assert result["allowed"] is False
        assert result["reason"] == "limit_reached"


# ─────────────────────────────────────────────────────
# Pro enforcement
# ─────────────────────────────────────────────────────
class TestProLimits:
    def test_pro_serp_within_limit(self):
        user = _make_user("pro", {"serp_queries": 100})
        result = _make_limiter().check_limit(user, "serp_query")
        assert result["allowed"] is True
        assert result["remaining"] >= 4000

    def test_pro_enrichment_within_limit(self):
        user = _make_user("pro", {"enrichment_calls": 200})
        result = _make_limiter().check_limit(user, "enrichment_call")
        assert result["allowed"] is True

    def test_pro_serp_at_5000_blocked(self):
        user = _make_user("pro", {"serp_queries": 5000})
        result = _make_limiter().check_limit(user, "serp_query")
        assert result["allowed"] is False


# ─────────────────────────────────────────────────────
# Enterprise — always allowed
# ─────────────────────────────────────────────────────
class TestEnterpriseLimits:
    def test_enterprise_serp_unlimited(self):
        user = _make_user("enterprise", {"serp_queries": 999_999})
        result = _make_limiter().check_limit(user, "serp_query")
        assert result["allowed"] is True
        assert result["limit"] == -1

    def test_enterprise_enrichment_unlimited(self):
        user = _make_user("enterprise", {"enrichment_calls": 999_999})
        result = _make_limiter().check_limit(user, "enrichment_call")
        assert result["allowed"] is True
        assert result["limit"] == -1


# ─────────────────────────────────────────────────────
# increment_usage updates the new counters
# ─────────────────────────────────────────────────────
class TestIncrementUsage:
    def test_serp_increment(self):
        limiter = _make_limiter()
        user = _make_user("pro", {"serp_queries": 5})
        limiter.increment_usage(user, "serp_query")
        assert user.usage_this_month["serp_queries"] == 6
        limiter.db.commit.assert_called()

    def test_enrichment_increment(self):
        limiter = _make_limiter()
        user = _make_user("pro", {"enrichment_calls": 10})
        limiter.increment_usage(user, "enrichment_call")
        assert user.usage_this_month["enrichment_calls"] == 11

    def test_unknown_action_does_not_crash(self):
        limiter = _make_limiter()
        user = _make_user("pro", {})
        limiter.increment_usage(user, "completely_unknown_action")
        # Existing keys preserved, no key added
        assert user.usage_this_month == {}


# ─────────────────────────────────────────────────────
# Backward compat — Phase 1-10 actions still work
# ─────────────────────────────────────────────────────
class TestBackwardCompat:
    def test_discover_leads_still_works(self):
        user = _make_user("trial", {"leads_discovered": 5})
        result = _make_limiter().check_limit(user, "discover_leads")
        assert result["allowed"] is True

    def test_send_message_still_works(self):
        user = _make_user("trial", {"messages_sent": 5})
        result = _make_limiter().check_limit(user, "send_message")
        assert result["allowed"] is False  # at limit

    def test_unknown_action_defaults_to_allowed(self):
        user = _make_user("pro", {})
        result = _make_limiter().check_limit(user, "totally_new_action")
        assert result["allowed"] is True
