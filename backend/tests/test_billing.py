"""
HUNTER.OS - Billing & Plan Limits Tests
"""
import pytest
from app.services.plan_limiter import PlanLimiter


class TestPlanLimiter:
    def test_trial_limits(self, db, test_user):
        """Test trial plan has correct limits."""
        test_user.plan = "trial"
        db.commit()

        limiter = PlanLimiter(db)
        result = limiter.check_limit(test_user, "discover_leads")
        assert result["allowed"] is True

    def test_trial_limit_exceeded(self, db, test_user):
        """Test trial limit enforcement after exceeding."""
        test_user.plan = "trial"
        test_user.usage_this_month = {"leads_discovered": 10}
        db.commit()

        limiter = PlanLimiter(db)
        result = limiter.check_limit(test_user, "discover_leads")
        assert result["allowed"] is False

    def test_pro_unlimited(self, db, test_user):
        """Test pro plan has much higher limits."""
        test_user.plan = "pro"
        test_user.usage_this_month = {"leads_discovered": 100}
        db.commit()

        limiter = PlanLimiter(db)
        assert limiter.check_limit(test_user, "leads_per_month")

    def test_usage_summary(self, db, test_user):
        """Test usage summary generation."""
        test_user.plan = "trial"
        test_user.usage_this_month = {"leads_discovered": 5, "messages_sent": 2}
        db.commit()

        limiter = PlanLimiter(db)
        summary = limiter.get_usage_summary(test_user)
        assert "plan" in summary
        assert "usage" in summary


class TestBillingAPI:
    def test_get_usage(self, client, auth_headers):
        """Test billing usage endpoint."""
        res = client.get("/api/v1/billing/usage", headers=auth_headers)
        assert res.status_code == 200

    def test_get_plans(self, client, auth_headers):
        """Test billing plans endpoint."""
        res = client.get("/api/v1/billing/plans", headers=auth_headers)
        assert res.status_code == 200
