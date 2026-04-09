"""
HUNTER.OS - Campaign API Tests
"""
import pytest
from app.models.campaign import Campaign


class TestCampaigns:
    def test_create_campaign(self, client, auth_headers):
        """Test campaign creation."""
        res = client.post("/api/v1/campaigns", json={
            "name": "Test Campaign",
            "description": "A test campaign",
            "workflow_steps": [
                {"step": 1, "channel": "email", "delay_hours": 0},
                {"step": 2, "channel": "linkedin_visit", "delay_hours": 24},
            ],
            "tags": ["test"],
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "draft"

    def test_list_campaigns(self, client, auth_headers):
        """Test listing campaigns."""
        client.post("/api/v1/campaigns", json={
            "name": "Camp1",
            "workflow_steps": [],
        }, headers=auth_headers)

        res = client.get("/api/v1/campaigns", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_activate_campaign(self, client, auth_headers):
        """Test activating a campaign."""
        create_res = client.post("/api/v1/campaigns", json={
            "name": "ActivateMe",
            "workflow_steps": [{"step": 1, "channel": "email", "delay_hours": 0}],
        }, headers=auth_headers)
        cid = create_res.json()["id"]

        res = client.post(f"/api/v1/campaigns/{cid}/activate", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    def test_pause_campaign(self, client, auth_headers):
        """Test pausing a campaign."""
        create_res = client.post("/api/v1/campaigns", json={
            "name": "PauseMe",
            "workflow_steps": [{"step": 1, "channel": "email", "delay_hours": 0}],
        }, headers=auth_headers)
        cid = create_res.json()["id"]

        # Activate first
        client.post(f"/api/v1/campaigns/{cid}/activate", headers=auth_headers)

        # Then pause
        res = client.post(f"/api/v1/campaigns/{cid}/pause", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "paused"


class TestABTesting:
    def test_ab_variant_stats(self, client, auth_headers, db, test_user):
        """Test A/B variant stats calculation."""
        from app.services.ab_testing import ABTestingEngine

        campaign = Campaign(
            user_id=test_user.id,
            name="AB Test Campaign",
            status="active",
            ab_variants=[
                {"variant_id": "a", "template": "Template A", "weight": 1.0},
                {"variant_id": "b", "template": "Template B", "weight": 1.0},
            ],
            workflow_steps=[],
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        ab = ABTestingEngine(db)

        # Record events
        for _ in range(30):
            ab.record_event(campaign.id, "a", "email", "sent")
        for _ in range(10):
            ab.record_event(campaign.id, "a", "email", "replied")

        for _ in range(30):
            ab.record_event(campaign.id, "b", "email", "sent")
        for _ in range(5):
            ab.record_event(campaign.id, "b", "email", "replied")

        stats = ab.get_variant_stats(campaign.id)
        assert "a" in stats
        assert "b" in stats
        assert stats["a"]["reply_rate"] > stats["b"]["reply_rate"]
