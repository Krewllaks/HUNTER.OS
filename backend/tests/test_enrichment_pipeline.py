"""
HUNTER.OS - Enrichment Pipeline Tests
Tests the multi-stage lead enrichment: footprint scan → scoring boost → content analysis.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.enrichment_pipeline import EnrichmentPipeline
from app.models.lead import Lead


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def db(setup_db):
    """Provide a clean database session."""
    from tests.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def pipeline(db):
    return EnrichmentPipeline(db)


@pytest.fixture
def test_lead(db):
    """Create a test lead for enrichment."""
    from app.models.user import User
    from app.core.security import hash_password

    user = User(email="enrich@test.com", hashed_password=hash_password("pass"), full_name="Tester")
    db.add(user)
    db.commit()
    db.refresh(user)

    lead = Lead(
        user_id=user.id,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@techcorp.com",
        linkedin_url="https://linkedin.com/in/jane-smith",
        company_name="TechCorp",
        title="VP Engineering",
        status="researched",
        intent_score=70.0,  # Phase 11: must be >= INTENT_SCORE_THRESHOLD_ENRICHMENT (60)
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


# ── Social Proof Boost Tests ─────────────────────────────

class TestSocialProofBoost:
    def test_no_profiles_no_boost(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = []
        assert pipeline._calculate_social_proof_boost(lead) == 0.0

    def test_none_profiles_no_boost(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = None
        assert pipeline._calculate_social_proof_boost(lead) == 0.0

    def test_linkedin_boost(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = [{"platform": "linkedin", "url": "http://linkedin.com/in/x"}]
        boost = pipeline._calculate_social_proof_boost(lead)
        assert boost >= 5.0  # LinkedIn gives +5

    def test_multiple_platforms_boost(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = [
            {"platform": "linkedin", "url": "url"},
            {"platform": "twitter", "url": "url"},
            {"platform": "github", "url": "url"},
        ]
        boost = pipeline._calculate_social_proof_boost(lead)
        # LinkedIn(5) + Twitter(3) + GitHub(3) + breadth_3_platforms(2) = 13
        assert boost == 13.0

    def test_breadth_bonus_5_plus(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = [
            {"platform": "linkedin", "url": "url"},
            {"platform": "twitter", "url": "url"},
            {"platform": "github", "url": "url"},
            {"platform": "medium", "url": "url"},
            {"platform": "reddit", "url": "url"},
        ]
        boost = pipeline._calculate_social_proof_boost(lead)
        # LinkedIn(5) + Twitter(3) + GitHub(3) + Medium(3) + breadth_5(5) = 19
        assert boost >= 19.0

    def test_content_creator_bonus(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = [
            {"platform": "youtube", "url": "url", "category": "content"},
        ]
        boost = pipeline._calculate_social_proof_boost(lead)
        # No named platform bonus, but category content gives +3
        assert boost >= 3.0

    def test_boost_capped_at_25(self, pipeline):
        lead = MagicMock()
        lead.social_profiles = [
            {"platform": "linkedin", "url": "url"},
            {"platform": "twitter", "url": "url"},
            {"platform": "github", "url": "url"},
            {"platform": "medium", "url": "url", "category": "content"},
            {"platform": "producthunt", "url": "url"},
            {"platform": "crunchbase", "url": "url"},
            {"platform": "substack", "url": "url"},
            {"platform": "indiehackers", "url": "url"},
        ]
        boost = pipeline._calculate_social_proof_boost(lead)
        assert boost <= 25.0


# ── Enrich Lead Tests ────────────────────────────────────

class TestEnrichLead:
    @pytest.mark.asyncio
    @patch("app.services.enrichment_pipeline.DigitalFootprintScanner")
    async def test_enrich_lead_success(self, MockScanner, pipeline, test_lead, db):
        mock_scanner = MockScanner.return_value
        mock_scanner.scan_lead = AsyncMock(return_value={
            "profiles": [
                {"platform": "GitHub", "url": "https://github.com/janesmith", "username": "janesmith", "verified": True, "category": "developer", "sales_relevance": 0.9},
                {"platform": "Twitter", "url": "https://x.com/janesmith", "username": "janesmith", "verified": True, "category": "social", "sales_relevance": 0.85},
            ],
            "footprint_score": 35.0,
        })
        pipeline.scanner = mock_scanner

        result = await pipeline.enrich_lead(test_lead.id)

        assert result["status"] == "success"
        assert result["lead_id"] == test_lead.id

        # Verify lead was updated
        db.refresh(test_lead)
        assert test_lead.social_profiles is not None
        assert len(test_lead.social_profiles) == 2
        assert test_lead.digital_footprint_score == 35.0
        assert test_lead.footprint_scanned_at is not None
        # Score should be boosted from original 50
        assert test_lead.intent_score > 50.0

    @pytest.mark.asyncio
    async def test_enrich_nonexistent_lead(self, pipeline):
        result = await pipeline.enrich_lead(99999)
        assert result["status"] == "error"
        assert result["reason"] == "lead_not_found"

    @pytest.mark.asyncio
    @patch("app.services.enrichment_pipeline.DigitalFootprintScanner")
    async def test_enrich_lead_scan_failure(self, MockScanner, pipeline, test_lead, db):
        """Pipeline should continue even if footprint scan fails."""
        mock_scanner = MockScanner.return_value
        mock_scanner.scan_lead = AsyncMock(side_effect=Exception("Network error"))
        pipeline.scanner = mock_scanner

        result = await pipeline.enrich_lead(test_lead.id)

        # Should still complete (with partial success)
        assert result["status"] == "success"
        scan_step = next(s for s in result["steps"] if s["step"] == "footprint_scan")
        assert scan_step["status"] == "failed"

    @pytest.mark.asyncio
    @patch("app.services.enrichment_pipeline.DigitalFootprintScanner")
    async def test_score_boost_capped_at_100(self, MockScanner, pipeline, test_lead, db):
        """Intent score should not exceed 100 after boost."""
        test_lead.intent_score = 95.0
        db.commit()

        mock_scanner = MockScanner.return_value
        mock_scanner.scan_lead = AsyncMock(return_value={
            "profiles": [
                {"platform": "linkedin", "url": "url", "username": "x", "verified": True, "category": "professional", "sales_relevance": 0.9},
                {"platform": "github", "url": "url", "username": "x", "verified": True, "category": "developer", "sales_relevance": 0.9},
                {"platform": "twitter", "url": "url", "username": "x", "verified": True, "category": "social", "sales_relevance": 0.85},
            ],
            "footprint_score": 50.0,
        })
        pipeline.scanner = mock_scanner

        await pipeline.enrich_lead(test_lead.id)
        db.refresh(test_lead)
        assert test_lead.intent_score <= 100.0


# ── Batch Enrich Tests ───────────────────────────────────

class TestBatchEnrich:
    @pytest.mark.asyncio
    @patch("app.services.enrichment_pipeline.DigitalFootprintScanner")
    async def test_batch_enrich(self, MockScanner, pipeline, test_lead, db):
        mock_scanner = MockScanner.return_value
        mock_scanner.scan_lead = AsyncMock(return_value={
            "profiles": [],
            "footprint_score": 0.0,
        })
        pipeline.scanner = mock_scanner

        results = await pipeline.enrich_leads_batch([test_lead.id])
        assert len(results) == 1
        assert results[0]["lead_id"] == test_lead.id
