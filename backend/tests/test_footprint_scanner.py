"""
HUNTER.OS - Digital Footprint Scanner Tests
Tests username extraction, scoring, and site checking logic.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.services.footprint_scanner import DigitalFootprintScanner, SiteResult


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def scanner():
    return DigitalFootprintScanner(concurrency=5, timeout_seconds=5)


@pytest.fixture
def mock_lead():
    """Create a mock lead object with typical data."""
    lead = MagicMock()
    lead.id = 1
    lead.email = "john.doe@example.com"
    lead.linkedin_url = "https://linkedin.com/in/john-doe-abc123"
    lead.first_name = "John"
    lead.last_name = "Doe"
    return lead


@pytest.fixture
def mock_lead_minimal():
    """Lead with minimal data."""
    lead = MagicMock()
    lead.id = 2
    lead.email = None
    lead.linkedin_url = None
    lead.first_name = None
    lead.last_name = None
    return lead


# ── Username Extraction Tests ────────────────────────────

class TestExtractUsernames:
    def test_email_prefix_extraction(self, scanner, mock_lead):
        usernames = scanner.extract_usernames(mock_lead)
        assert "john.doe" in usernames
        assert "johndoe" in usernames

    def test_email_dash_variation(self, scanner, mock_lead):
        usernames = scanner.extract_usernames(mock_lead)
        assert "john-doe" in usernames

    def test_linkedin_slug_extraction(self, scanner, mock_lead):
        usernames = scanner.extract_usernames(mock_lead)
        # Should extract john-doe, removing the -abc123 hash
        assert "john-doe" in usernames
        assert "johndoe" in usernames

    def test_name_combinations(self, scanner, mock_lead):
        usernames = scanner.extract_usernames(mock_lead)
        assert "johndoe" in usernames
        assert "john.doe" in usernames
        assert "john-doe" in usernames
        assert "jdoe" in usernames

    def test_minimal_lead_returns_empty(self, scanner, mock_lead_minimal):
        usernames = scanner.extract_usernames(mock_lead_minimal)
        assert len(usernames) == 0

    def test_email_only_lead(self, scanner):
        lead = MagicMock()
        lead.id = 3
        lead.email = "alice@company.com"
        lead.linkedin_url = None
        lead.first_name = None
        lead.last_name = None
        usernames = scanner.extract_usernames(lead)
        assert "alice" in usernames

    def test_short_usernames_filtered(self, scanner):
        lead = MagicMock()
        lead.id = 4
        lead.email = "a@x.com"
        lead.linkedin_url = None
        lead.first_name = None
        lead.last_name = None
        usernames = scanner.extract_usernames(lead)
        # "a" is too short (< 2 chars)
        assert "a" not in usernames

    def test_linkedin_with_numbers_stripped(self, scanner):
        lead = MagicMock()
        lead.id = 5
        lead.email = None
        lead.linkedin_url = "https://linkedin.com/in/sarah-connor-4a2b8c"
        lead.first_name = None
        lead.last_name = None
        usernames = scanner.extract_usernames(lead)
        assert "sarah-connor" in usernames
        assert "sarahconnor" in usernames

    def test_dedup(self, scanner, mock_lead):
        """Same username from multiple sources should appear once."""
        usernames = scanner.extract_usernames(mock_lead)
        assert len(usernames) == len(set(usernames))


# ── Footprint Score Tests ────────────────────────────────

class TestCalcFootprintScore:
    def test_empty_profiles(self, scanner):
        assert scanner._calc_footprint_score([]) == 0.0

    def test_single_high_value_profile(self, scanner):
        profiles = [
            SiteResult("LinkedIn", "url", "user", True, "professional", 0.9),
        ]
        score = scanner._calc_footprint_score(profiles)
        assert score > 0
        # 0.9*10 (base) + 1*4 (diversity) + 1*5 (hv) = 18
        assert score == 18.0

    def test_multiple_profiles_diverse(self, scanner):
        profiles = [
            SiteResult("LinkedIn", "url", "user", True, "professional", 0.9),
            SiteResult("GitHub", "url", "user", True, "developer", 0.9),
            SiteResult("Twitter", "url", "user", True, "social", 0.85),
            SiteResult("Medium", "url", "user", True, "content", 0.7),
        ]
        score = scanner._calc_footprint_score(profiles)
        # base = (0.9+0.9+0.85+0.7)*10 = 33.5
        # diversity = 4 categories * 4 = 16
        # hv_bonus = 4 * 5 = 20  (LinkedIn, GitHub, Twitter, Medium)
        # total = 69.5 (capped at 100)
        assert score == 69.5

    def test_score_capped_at_100(self, scanner):
        """Even with many profiles, score caps at 100."""
        profiles = [
            SiteResult(f"Platform{i}", "url", "user", True, f"cat{i}", 0.9)
            for i in range(20)
        ]
        score = scanner._calc_footprint_score(profiles)
        assert score <= 100.0

    def test_high_value_bonus_only_for_known_platforms(self, scanner):
        profiles = [
            SiteResult("RandomSite", "url", "user", True, "other", 0.5),
        ]
        score = scanner._calc_footprint_score(profiles)
        # base=5, diversity=4, hv=0 → 9
        assert score == 9.0


# ── Site Check Tests ─────────────────────────────────────

class TestCheckSite:
    @pytest.mark.asyncio
    async def test_regex_mismatch_returns_not_found(self, scanner):
        """Username that doesn't match site regex should return not found."""
        import aiohttp

        session = MagicMock()
        site_config = {
            "url": "https://example.com/{}",
            "errorType": "status_code",
            "regexCheck": "^[a-zA-Z0-9]+$",
            "category": "social",
            "sales_relevance": 0.5,
        }
        # Username with dots doesn't match regex
        result = await scanner._check_site(session, "TestSite", site_config, "john.doe")
        assert result.found is False
        assert result.error == "regex_mismatch"

    @pytest.mark.asyncio
    async def test_status_code_found(self, scanner):
        """HTTP 200 for status_code detection should mean found."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        site_config = {
            "url": "https://github.com/{}",
            "errorType": "status_code",
            "category": "developer",
            "sales_relevance": 0.9,
        }

        result = await scanner._check_site(mock_session, "GitHub", site_config, "testuser")
        assert result.platform == "GitHub"
        assert result.found is True

    @pytest.mark.asyncio
    async def test_status_code_not_found(self, scanner):
        """HTTP 404 for status_code detection should mean not found."""
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        site_config = {
            "url": "https://github.com/{}",
            "errorType": "status_code",
            "category": "developer",
            "sales_relevance": 0.9,
        }

        result = await scanner._check_site(mock_session, "GitHub", site_config, "nonexistentuser")
        assert result.found is False

    @pytest.mark.asyncio
    async def test_message_detection_found(self, scanner):
        """When error message NOT present, user is found."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="<html><body>Profile of testuser</body></html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        site_config = {
            "url": "https://example.com/{}",
            "errorType": "message",
            "errorMsg": ["User not found", "Page not available"],
            "category": "social",
            "sales_relevance": 0.5,
        }

        result = await scanner._check_site(mock_session, "ExampleSite", site_config, "testuser")
        assert result.found is True

    @pytest.mark.asyncio
    async def test_message_detection_not_found(self, scanner):
        """When error message IS present, user is not found."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="<html><body>User not found</body></html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        site_config = {
            "url": "https://example.com/{}",
            "errorType": "message",
            "errorMsg": ["User not found", "Page not available"],
            "category": "social",
            "sales_relevance": 0.5,
        }

        result = await scanner._check_site(mock_session, "ExampleSite", site_config, "nonexistent")
        assert result.found is False

    @pytest.mark.asyncio
    async def test_timeout_returns_not_found(self, scanner):
        """Timeout should return not found with error."""
        mock_session = MagicMock()

        async def raise_timeout(*args, **kwargs):
            raise asyncio.TimeoutError()

        mock_cm = MagicMock()
        mock_cm.__aenter__ = raise_timeout
        mock_session.request = MagicMock(return_value=mock_cm)

        site_config = {
            "url": "https://slow.com/{}",
            "errorType": "status_code",
            "category": "other",
            "sales_relevance": 0.3,
        }

        result = await scanner._check_site(mock_session, "SlowSite", site_config, "user")
        assert result.found is False
        assert result.error == "timeout"


# ── Scan Lead Tests ──────────────────────────────────────

class TestScanLead:
    @pytest.mark.asyncio
    async def test_scan_lead_no_usernames(self, scanner, mock_lead_minimal):
        result = await scanner.scan_lead(mock_lead_minimal)
        assert result["profiles"] == []
        assert result["footprint_score"] == 0.0
        assert result["usernames_checked"] == []

    @pytest.mark.asyncio
    @patch("app.services.footprint_scanner.DigitalFootprintScanner.scan_username")
    async def test_scan_lead_deduplicates_platforms(self, mock_scan, scanner, mock_lead):
        """Same platform from different usernames should only appear once."""
        mock_scan.return_value = [
            SiteResult("GitHub", "https://github.com/johndoe", "johndoe", True, "developer", 0.9),
        ]
        result = await scanner.scan_lead(mock_lead)
        # Even though scan runs for multiple usernames, GitHub should appear once
        github_profiles = [p for p in result["profiles"] if p["platform"] == "GitHub"]
        assert len(github_profiles) <= 1

    @pytest.mark.asyncio
    @patch("app.services.footprint_scanner.DigitalFootprintScanner.scan_username")
    async def test_scan_lead_with_custom_usernames(self, mock_scan, scanner, mock_lead):
        mock_scan.return_value = []
        result = await scanner.scan_lead(mock_lead, custom_usernames=["custom_user"])
        assert "custom_user" in result["usernames_checked"]
