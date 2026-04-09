"""
HUNTER.OS - Hunt Service Tests
Tests the hunt orchestration pipeline: research → score → personalize → enrich.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.hunt_service import HuntService
from app.models.lead import Lead
from app.models.user import User
from app.core.security import hash_password


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def db(setup_db):
    from tests.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db):
    user = User(
        email="hunter@test.com",
        hashed_password=hash_password("testpass"),
        full_name="Hunter Test",
        plan="pro",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def hunt_service(db):
    return HuntService(db)


# ── Domain Research Tests ────────────────────────────────

class TestDomainResearch:
    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    async def test_research_domain_parses_json(self, mock_create_agent, hunt_service):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value='{"company_name": "Acme", "industry": "SaaS"}')
        mock_create_agent.return_value = mock_agent

        result = await hunt_service._research_domain(
            mock_agent, "acme.com", ["technographics"]
        )
        assert result["company_name"] == "Acme"
        assert result["domain"] == "acme.com"

    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    async def test_research_domain_handles_non_json(self, mock_create_agent, hunt_service):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="Some raw text about the company")
        mock_create_agent.return_value = mock_agent

        result = await hunt_service._research_domain(
            mock_agent, "unknown.com", ["news"]
        )
        assert result["domain"] == "unknown.com"
        assert "raw_research" in result

    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    async def test_research_domain_sets_default_company_name(self, mock_create_agent, hunt_service):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value='{"industry": "tech"}')
        mock_create_agent.return_value = mock_agent

        result = await hunt_service._research_domain(
            mock_agent, "coolstartup.io", ["technographics"]
        )
        assert result["company_name"] == "Coolstartup"


# ── LinkedIn Research Tests ──────────────────────────────

class TestLinkedInResearch:
    @pytest.mark.asyncio
    async def test_research_linkedin_parses_json(self, hunt_service):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value='{"first_name": "John", "last_name": "Doe"}')

        result = await hunt_service._research_linkedin(
            mock_agent, "https://linkedin.com/in/john-doe", ["social_engagement"]
        )
        assert result["first_name"] == "John"
        assert result["linkedin_url"] == "https://linkedin.com/in/john-doe"

    @pytest.mark.asyncio
    async def test_research_linkedin_handles_failure(self, hunt_service):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="Could not parse profile")

        result = await hunt_service._research_linkedin(
            mock_agent, "https://linkedin.com/in/unknown", ["news"]
        )
        assert "raw_research" in result
        assert result["linkedin_url"] == "https://linkedin.com/in/unknown"


# ── Save Lead Tests ──────────────────────────────────────

class TestSaveLead:
    def test_save_lead_basic(self, hunt_service, test_user, db):
        lead_data = {
            "company_name": "TestCorp",
            "domain": "testcorp.com",
            "email": "contact@testcorp.com",
            "first_name": "Alice",
            "last_name": "Wonder",
            "title": "CEO",
            "tech_stack": ["Python", "FastAPI"],
            "news": [{"headline": "Funding round"}],
        }
        lead = hunt_service._save_lead(test_user.id, lead_data, None, "domain_hunt")
        db.commit()

        assert lead.id is not None
        assert lead.company_name == "TestCorp"
        assert lead.email == "contact@testcorp.com"
        assert lead.first_name == "Alice"
        assert lead.source == "domain_hunt"
        assert lead.status == "researched"
        assert "Python" in lead.technographics

    def test_save_lead_with_name_field(self, hunt_service, test_user, db):
        lead_data = {
            "name": "Bob Builder",
            "company": "BuildIt",
        }
        lead = hunt_service._save_lead(test_user.id, lead_data, None, "manual")
        db.commit()

        assert lead.first_name == "Bob"
        assert lead.last_name == "Builder"
        assert lead.company_name == "BuildIt"

    def test_save_lead_with_buying_committee(self, hunt_service, test_user, db):
        lead_data = {
            "company_name": "BigCorp",
            "buying_committee": [
                {"name": "CTO", "role": "Technical", "email": "cto@big.com"},
                {"name": "VP Sales", "role": "Commercial"},
            ],
        }
        lead = hunt_service._save_lead(test_user.id, lead_data, None, "linkedin_hunt")
        db.commit()

        assert len(lead.buying_committee) == 2
        assert lead.buying_committee[0].name == "CTO"

    def test_save_lead_with_campaign_id(self, hunt_service, test_user, db):
        from app.models.campaign import Campaign
        campaign = Campaign(user_id=test_user.id, name="Test Campaign")
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        lead_data = {"company_name": "CampaignTarget"}
        lead = hunt_service._save_lead(test_user.id, lead_data, campaign.id, "domain_hunt")
        db.commit()

        assert lead.campaign_id == campaign.id


# ── Full Hunt Pipeline Tests ─────────────────────────────

class TestStartHunt:
    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    @patch.object(HuntService, "_research_domain")
    async def test_start_hunt_domain(self, mock_research, mock_create_agent, hunt_service, test_user, db):
        mock_research.return_value = {
            "company_name": "HuntedCo",
            "domain": "hunted.com",
            "email": "hi@hunted.com",
            "first_name": "Target",
            "last_name": "Lead",
            "tech_stack": [],
            "news": [],
        }
        # Mock scoring agent
        hunt_service.scoring_agent.score_lead = AsyncMock(return_value={
            "final_score": 75,
            "confidence": 80,
            "icp_match_score": 70,
        })
        # Mock personalization agent
        hunt_service.personalization_agent.generate_message = AsyncMock(return_value={
            "body": "Hello, I noticed your company..."
        })

        results = await hunt_service.start_hunt(
            user_id=test_user.id,
            target_domains=["hunted.com"],
            auto_score=True,
            auto_personalize=True,
        )

        assert results["leads_researched"] == 1
        assert results["leads_scored"] == 1
        assert len(results["errors"]) == 0

    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    @patch.object(HuntService, "_research_domain")
    async def test_start_hunt_error_handling(self, mock_research, mock_create_agent, hunt_service, test_user):
        mock_research.side_effect = Exception("Research failed")

        results = await hunt_service.start_hunt(
            user_id=test_user.id,
            target_domains=["fail.com"],
        )

        assert results["leads_researched"] == 0
        assert len(results["errors"]) == 1
        assert results["errors"][0]["domain"] == "fail.com"

    @pytest.mark.asyncio
    @patch("app.services.hunt_service.create_research_agent")
    async def test_start_hunt_empty_targets(self, mock_create_agent, hunt_service, test_user):
        results = await hunt_service.start_hunt(user_id=test_user.id)

        assert results["leads_researched"] == 0
        assert results["leads_scored"] == 0
        assert len(results["errors"]) == 0
