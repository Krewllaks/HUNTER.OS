"""
HUNTER.OS - PlanLimiter Comprehensive Tests
AAA Pattern | Happy Path + Edge Cases + Boundary Values
Following the "Test Piramidi" methodology from @ersinkoc
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.services.plan_limiter import PlanLimiter, PLAN_LIMITS
from app.models.user import User
from app.core.security import hash_password as get_password_hash


# ── Helper Fixtures ─────────────────────────────────────
@pytest.fixture
def trial_user(db) -> User:
    """Create a trial user with fresh usage."""
    user = User(
        email="trial@hunter.os",
        full_name="Trial User",
        hashed_password=get_password_hash("test123"),
        plan="trial",
        usage_this_month={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def pro_user(db) -> User:
    """Create a pro plan user."""
    user = User(
        email="pro@hunter.os",
        full_name="Pro User",
        hashed_password=get_password_hash("test123"),
        plan="pro",
        usage_this_month={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def enterprise_user(db) -> User:
    """Create an enterprise plan user."""
    user = User(
        email="enterprise@hunter.os",
        full_name="Enterprise User",
        hashed_password=get_password_hash("test123"),
        plan="enterprise",
        usage_this_month={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def limiter(db) -> PlanLimiter:
    return PlanLimiter(db)


# ── Unit Tests: check_limit ─────────────────────────────
class TestCheckLimit:
    """Test the core limit checking logic — tuğla (brick) level."""

    # Happy Path
    def test_trial_user_first_lead_allowed(self, limiter, trial_user):
        """Fresh trial user should be allowed to discover leads."""
        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["allowed"] is True
        assert result["remaining"] == 9  # 10 limit - 0 used - 1 requested
        assert result["limit"] == 10

    def test_pro_user_unlimited_leads(self, limiter, pro_user):
        """Pro user should have unlimited leads."""
        result = limiter.check_limit(pro_user, "discover_leads")
        assert result["allowed"] is True
        assert result["remaining"] == -1
        assert result["limit"] == -1

    def test_enterprise_unlimited_everything(self, limiter, enterprise_user):
        """Enterprise should have unlimited leads and messages."""
        leads = limiter.check_limit(enterprise_user, "discover_leads")
        msgs = limiter.check_limit(enterprise_user, "send_message")
        assert leads["allowed"] is True
        assert msgs["allowed"] is True

    # Boundary Values — sınır değerleri
    def test_trial_at_exact_limit(self, db, limiter, trial_user):
        """Trial user at exactly 10 leads should NOT be allowed to add more."""
        # ARRANGE
        trial_user.usage_this_month = {"leads_discovered": 10}
        db.commit()

        # ACT
        result = limiter.check_limit(trial_user, "discover_leads")

        # ASSERT
        assert result["allowed"] is False
        assert result["reason"] == "limit_reached"

    def test_trial_at_9_leads_allows_one_more(self, db, limiter, trial_user):
        """Trial user at 9/10 leads should be allowed exactly 1 more."""
        trial_user.usage_this_month = {"leads_discovered": 9}
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads", count=1)
        assert result["allowed"] is True
        assert result["remaining"] == 0  # 10 - 9 - 1 = 0

    def test_trial_at_9_leads_denies_two_more(self, db, limiter, trial_user):
        """Trial user at 9/10 should be denied if requesting 2."""
        trial_user.usage_this_month = {"leads_discovered": 9}
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads", count=2)
        assert result["allowed"] is False

    def test_trial_messages_limit_5(self, db, limiter, trial_user):
        """Trial message limit is 5."""
        trial_user.usage_this_month = {"messages_sent": 5}
        db.commit()

        result = limiter.check_limit(trial_user, "send_message")
        assert result["allowed"] is False
        assert result["limit"] == 5

    # Feature Locks
    def test_trial_linkedin_locked(self, limiter, trial_user):
        """Trial user should NOT have LinkedIn automation."""
        result = limiter.check_limit(trial_user, "linkedin_action")
        assert result["allowed"] is False
        assert result["reason"] == "feature_locked"

    def test_pro_linkedin_allowed(self, limiter, pro_user):
        """Pro user SHOULD have LinkedIn automation."""
        result = limiter.check_limit(pro_user, "linkedin_action")
        assert result["allowed"] is True

    def test_trial_email_locked(self, limiter, trial_user):
        """Trial user should NOT have email sending."""
        result = limiter.check_limit(trial_user, "send_email")
        assert result["allowed"] is False

    def test_pro_email_allowed(self, limiter, pro_user):
        """Pro user SHOULD have email sending."""
        result = limiter.check_limit(pro_user, "send_email")
        assert result["allowed"] is True

    # Edge Cases
    def test_unknown_action_always_allowed(self, limiter, trial_user):
        """Unknown action names should be allowed (no restriction)."""
        result = limiter.check_limit(trial_user, "some_random_action")
        assert result["allowed"] is True

    def test_user_with_no_plan_defaults_to_trial(self, db, limiter, trial_user):
        """User with None plan should default to trial limits."""
        trial_user.plan = None
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["limit"] == 10  # trial limit

    def test_user_with_invalid_plan_defaults_to_trial(self, db, limiter, trial_user):
        """User with unknown plan name should default to trial limits."""
        trial_user.plan = "nonexistent_plan"
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["limit"] == 10

    def test_usage_as_none_treated_as_empty(self, db, limiter, trial_user):
        """None usage_this_month should be treated as empty dict."""
        trial_user.usage_this_month = None
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["allowed"] is True

    def test_product_limit_trial(self, db, limiter, trial_user):
        """Trial user can only create 1 product."""
        trial_user.usage_this_month = {"products_count": 1}
        db.commit()

        result = limiter.check_limit(trial_user, "create_product")
        assert result["allowed"] is False


# ── Trial Expiration Tests ──────────────────────────────
class TestTrialExpiration:
    """Test trial period expiration logic."""

    def test_expired_trial_blocks_everything(self, db, limiter, trial_user):
        """Expired trial should block all actions."""
        trial_user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["allowed"] is False
        assert result["reason"] == "trial_expired"

    def test_active_trial_allows_actions(self, db, limiter, trial_user):
        """Active trial (future end date) should allow actions."""
        trial_user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=7)
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["allowed"] is True

    def test_trial_no_end_date_allows_actions(self, db, limiter, trial_user):
        """Trial without end date set should allow actions."""
        trial_user.trial_ends_at = None
        db.commit()

        result = limiter.check_limit(trial_user, "discover_leads")
        assert result["allowed"] is True

    def test_pro_plan_ignores_trial_expiration(self, db, limiter, pro_user):
        """Pro plan should not check trial expiration."""
        pro_user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=100)
        db.commit()

        result = limiter.check_limit(pro_user, "discover_leads")
        assert result["allowed"] is True


# ── increment_usage Tests ───────────────────────────────
class TestIncrementUsage:
    """Test usage counter incrementation."""

    def test_increment_leads(self, db, limiter, trial_user):
        """Incrementing leads should increase counter."""
        limiter.increment_usage(trial_user, "discover_leads", count=3)
        db.refresh(trial_user)

        usage = trial_user.usage_this_month
        assert usage["leads_discovered"] == 3

    def test_increment_messages(self, db, limiter, trial_user):
        """Incrementing messages should increase counter."""
        limiter.increment_usage(trial_user, "send_message", count=2)
        db.refresh(trial_user)

        assert trial_user.usage_this_month["messages_sent"] == 2

    def test_cumulative_increment(self, db, limiter, trial_user):
        """Multiple increments should accumulate."""
        limiter.increment_usage(trial_user, "discover_leads", count=3)
        # Re-read from DB to get fresh state (SQLAlchemy JSON mutation)
        db.expire(trial_user)
        limiter.increment_usage(trial_user, "discover_leads", count=4)
        db.expire(trial_user)

        usage = limiter._get_usage(trial_user)
        assert usage["leads_discovered"] == 7

    def test_increment_from_none_usage(self, db, limiter, trial_user):
        """Incrementing when usage is None should start from 0."""
        trial_user.usage_this_month = None
        db.commit()

        limiter.increment_usage(trial_user, "discover_leads")
        db.refresh(trial_user)

        assert trial_user.usage_this_month["leads_discovered"] == 1


# ── get_usage_summary Tests ─────────────────────────────
class TestUsageSummary:
    """Test usage summary generation."""

    def test_summary_contains_plan(self, limiter, trial_user):
        """Summary should include plan name."""
        summary = limiter.get_usage_summary(trial_user)
        assert summary["plan"] == "trial"

    def test_summary_contains_limits(self, limiter, trial_user):
        """Summary should include plan limits."""
        summary = limiter.get_usage_summary(trial_user)
        assert summary["limits"]["leads_per_month"] == 10

    def test_trial_summary_has_days_remaining(self, db, limiter, trial_user):
        """Trial summary should show remaining days."""
        trial_user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=7)
        db.commit()

        summary = limiter.get_usage_summary(trial_user)
        assert "trial" in summary
        assert summary["trial"]["days_remaining"] >= 6  # allow 1 day rounding

    def test_pro_summary_no_trial_info(self, limiter, pro_user):
        """Pro plan summary should NOT have trial info."""
        summary = limiter.get_usage_summary(pro_user)
        assert summary["trial"] == {}


# ── require_limit (HTTP 402) Tests ──────────────────────
class TestRequireLimit:
    """Integration: test HTTP 402 guard for API endpoints."""

    def test_require_limit_raises_402_when_exceeded(self, db, limiter, trial_user):
        """Exceeding limit should raise HTTP 402 Payment Required."""
        trial_user.usage_this_month = {"leads_discovered": 10}
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            limiter.require_limit(trial_user, "discover_leads")

        assert exc_info.value.status_code == 402
        assert "plan_limit_exceeded" in str(exc_info.value.detail)

    def test_require_limit_passes_when_under_limit(self, limiter, trial_user):
        """Under limit should NOT raise any exception."""
        # Should not raise
        limiter.require_limit(trial_user, "discover_leads")

    def test_require_limit_402_includes_upgrade_url(self, db, limiter, trial_user):
        """402 response should include upgrade URL for FOMO conversion."""
        trial_user.usage_this_month = {"leads_discovered": 10}
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            limiter.require_limit(trial_user, "discover_leads")

        assert exc_info.value.detail["upgrade_url"] == "/pricing"


# ── PLAN_LIMITS Config Integrity Tests ──────────────────
class TestPlanConfig:
    """Verify plan configuration constants are correct."""

    def test_all_plans_exist(self):
        """All expected plans should be configured."""
        assert "trial" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "enterprise" in PLAN_LIMITS

    def test_trial_has_restrictive_limits(self):
        """Trial should have actual numeric limits, not unlimited."""
        trial = PLAN_LIMITS["trial"]
        assert trial["leads_per_month"] > 0  # not unlimited
        assert trial["messages_per_month"] > 0
        assert trial["products"] > 0

    def test_pro_has_unlimited_leads(self):
        """Pro plan should have unlimited leads."""
        assert PLAN_LIMITS["pro"]["leads_per_month"] == -1

    def test_enterprise_has_api_access(self):
        """Only Enterprise should have API access."""
        assert PLAN_LIMITS["trial"]["api_access"] is False
        assert PLAN_LIMITS["pro"]["api_access"] is False
        assert PLAN_LIMITS["enterprise"]["api_access"] is True

    def test_plan_hierarchy_makes_business_sense(self):
        """Higher plans should have >= features of lower plans."""
        trial = PLAN_LIMITS["trial"]
        pro = PLAN_LIMITS["pro"]
        ent = PLAN_LIMITS["enterprise"]

        # Pro >= Trial
        assert pro["team_members"] >= trial["team_members"]
        # Enterprise >= Pro
        assert ent["team_members"] >= pro["team_members"]
