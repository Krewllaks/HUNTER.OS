"""
HUNTER.OS - Lead API Tests
"""
import pytest
from app.models.lead import Lead


class TestLeads:
    def _create_lead(self, db, user_id, **kwargs):
        """Helper to create a lead directly in DB."""
        lead = Lead(
            user_id=user_id,
            first_name=kwargs.get("first_name", "Test"),
            last_name=kwargs.get("last_name", "Lead"),
            email=kwargs.get("email", "test@lead.com"),
            company_name=kwargs.get("company_name", "TestCorp"),
            industry=kwargs.get("industry", "Technology"),
            intent_score=kwargs.get("intent_score", 75.0),
            status=kwargs.get("status", "new"),
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    def test_list_leads(self, client, auth_headers, db, test_user):
        """Test listing leads."""
        self._create_lead(db, test_user.id)
        self._create_lead(db, test_user.id, email="test2@lead.com", first_name="Second")

        res = client.get("/api/v1/leads", headers=auth_headers)
        assert res.status_code == 200

    def test_get_lead(self, client, auth_headers, db, test_user):
        """Test getting a specific lead."""
        lead = self._create_lead(db, test_user.id)

        res = client.get(f"/api/v1/leads/{lead.id}", headers=auth_headers)
        assert res.status_code == 200

    def test_create_lead(self, client, auth_headers):
        """Test creating a lead via API."""
        res = client.post("/api/v1/leads", json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@doe.com",
            "company_name": "DoeCorp",
        }, headers=auth_headers)
        assert res.status_code == 201

    def test_update_lead(self, client, auth_headers, db, test_user):
        """Test updating a lead."""
        lead = self._create_lead(db, test_user.id)

        res = client.patch(f"/api/v1/leads/{lead.id}", json={
            "status": "contacted",
        }, headers=auth_headers)
        assert res.status_code == 200

    def test_delete_lead(self, client, auth_headers, db, test_user):
        """Test deleting a lead."""
        lead = self._create_lead(db, test_user.id)

        res = client.delete(f"/api/v1/leads/{lead.id}", headers=auth_headers)
        assert res.status_code in [200, 204]


class TestLeadScoring:
    def test_scoring_distribution(self, client, auth_headers, db, test_user):
        """Test scoring distribution endpoint."""
        # Create leads with different scores
        for score in [10, 30, 55, 80]:
            lead = Lead(
                user_id=test_user.id,
                first_name=f"Lead{score}",
                email=f"lead{score}@test.com",
                intent_score=score,
                status="new",
            )
            db.add(lead)
        db.commit()

        res = client.get("/api/v1/analytics/leads/scoring-distribution", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "distribution" in data
