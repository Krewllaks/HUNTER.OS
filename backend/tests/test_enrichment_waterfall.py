"""
Phase 11 — Enrichment waterfall + conditional gate tests.

Covers:
* LeadEnrichmentAPI.enrich_email — Apollo → PDL → local guess → Hunter → Snov
* LeadEnrichmentAPI._guess_email_patterns — MX validation success / failure
* EnrichmentPipeline.enrich_lead — conditional gate skips low-intent leads

NO real HTTP. NO real DNS lookups (dns.resolver patched).
"""
from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import lead_enrichment_api as enr_module
from app.services.lead_enrichment_api import LeadEnrichmentAPI
from app.services import enrichment_pipeline as pipe_module
from app.services.enrichment_pipeline import EnrichmentPipeline


def _run(coro):
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────
# enrich_email waterfall ordering
# ─────────────────────────────────────────────────────
class TestWaterfall:
    def test_apollo_hit_short_circuits_paid_providers(self):
        api = LeadEnrichmentAPI()
        apollo_hit = {"email": "ahmet@acme.com.tr", "source": "apollo"}

        with patch.object(enr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(enr_module, "cache_set", new=AsyncMock()), \
             patch.object(enr_module.settings, "APOLLO_API_KEY", "k"), \
             patch.object(enr_module.settings, "PDL_API_KEY", None), \
             patch.object(enr_module.settings, "HUNTER_IO_API_KEY", "h"), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_ID", "s"), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_SECRET", "s2"), \
             patch.object(enr_module.settings, "ROCKETREACH_API_KEY", "r"), \
             patch.object(enr_module.ApolloClient, "find_email",
                          new=AsyncMock(return_value=apollo_hit)), \
             patch.object(api, "_hunter_email_finder",
                          new=AsyncMock(side_effect=AssertionError("hunter must NOT run"))), \
             patch.object(api, "_snov_email_finder",
                          new=AsyncMock(side_effect=AssertionError("snov must NOT run"))), \
             patch.object(api, "_rocketreach_lookup",
                          new=AsyncMock(side_effect=AssertionError("rr must NOT run"))):
            result = _run(api.enrich_email("acme.com.tr", "Ahmet", "Yilmaz"))

        assert result["email"] == "ahmet@acme.com.tr"
        assert result["source"] == "apollo"

    def test_apollo_miss_pdl_does_not_run(self):
        """PDL only enriches when Apollo found an email — never replaces it."""
        api = LeadEnrichmentAPI()

        with patch.object(enr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(enr_module, "cache_set", new=AsyncMock()), \
             patch.object(enr_module.settings, "APOLLO_API_KEY", "k"), \
             patch.object(enr_module.settings, "PDL_API_KEY", "p"), \
             patch.object(enr_module.settings, "HUNTER_IO_API_KEY", None), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_ID", None), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_SECRET", None), \
             patch.object(enr_module.settings, "ROCKETREACH_API_KEY", None), \
             patch.object(enr_module.ApolloClient, "find_email",
                          new=AsyncMock(return_value=None)), \
             patch.object(enr_module.PDLClient, "enrich_person",
                          new=AsyncMock(side_effect=AssertionError("PDL must NOT run without anchor"))), \
             patch.object(api, "_guess_email_patterns", return_value=None):
            result = _run(api.enrich_email("acme.com.tr", "A", "Y"))

        assert result["email"] is None

    def test_apollo_hit_then_pdl_merges_profile(self):
        api = LeadEnrichmentAPI()
        apollo_hit = {"email": "a@b.com", "source": "apollo"}
        pdl_hit = {"job_title": "CTO", "skills": ["python"], "source": "pdl"}

        with patch.object(enr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(enr_module, "cache_set", new=AsyncMock()), \
             patch.object(enr_module.settings, "APOLLO_API_KEY", "k"), \
             patch.object(enr_module.settings, "PDL_API_KEY", "p"), \
             patch.object(enr_module.settings, "HUNTER_IO_API_KEY", None), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_ID", None), \
             patch.object(enr_module.settings, "ROCKETREACH_API_KEY", None), \
             patch.object(enr_module.ApolloClient, "find_email",
                          new=AsyncMock(return_value=apollo_hit)), \
             patch.object(enr_module.PDLClient, "enrich_person",
                          new=AsyncMock(return_value=pdl_hit)):
            result = _run(api.enrich_email("b.com", "A", "Y"))

        assert result["email"] == "a@b.com"
        assert result["source"] == "apollo"  # source NOT overwritten
        assert result["job_title"] == "CTO"
        assert result["skills"] == ["python"]

    def test_local_guess_runs_after_apollo_miss(self):
        api = LeadEnrichmentAPI()
        guess = {"email": "ahmet.yilmaz@acme.com", "confidence": 0.4, "source": "local_guess"}

        with patch.object(enr_module, "cache_get", new=AsyncMock(return_value=None)), \
             patch.object(enr_module, "cache_set", new=AsyncMock()), \
             patch.object(enr_module.settings, "APOLLO_API_KEY", "k"), \
             patch.object(enr_module.settings, "PDL_API_KEY", None), \
             patch.object(enr_module.settings, "HUNTER_IO_API_KEY", None), \
             patch.object(enr_module.settings, "SNOV_IO_CLIENT_ID", None), \
             patch.object(enr_module.settings, "ROCKETREACH_API_KEY", None), \
             patch.object(enr_module.ApolloClient, "find_email",
                          new=AsyncMock(return_value=None)), \
             patch.object(api, "_guess_email_patterns", return_value=guess):
            result = _run(api.enrich_email("acme.com", "Ahmet", "Yilmaz"))

        assert result["source"] == "local_guess"

    def test_cache_hit_short_circuits_entire_waterfall(self):
        api = LeadEnrichmentAPI()
        cached = {"email": "cached@x.com", "source": "apollo"}

        with patch.object(enr_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(enr_module, "cache_set", new=AsyncMock()), \
             patch.object(enr_module.ApolloClient, "find_email",
                          new=AsyncMock(side_effect=AssertionError("apollo must NOT run"))):
            result = _run(api.enrich_email("x.com", "C", "X"))

        assert result == cached


# ─────────────────────────────────────────────────────
# _guess_email_patterns
# ─────────────────────────────────────────────────────
class TestEmailGuess:
    def test_guess_returns_email_when_mx_resolves(self):
        api = LeadEnrichmentAPI()

        # Build a fake `dns.resolver` module that resolves successfully.
        fake_dns = types.ModuleType("dns")
        fake_resolver = types.ModuleType("dns.resolver")
        fake_resolver.resolve = MagicMock(return_value=[MagicMock()])
        fake_dns.resolver = fake_resolver

        with patch.dict(sys.modules, {"dns": fake_dns, "dns.resolver": fake_resolver}):
            result = api._guess_email_patterns("Ahmet", "Yilmaz", "acme.com.tr")

        assert result is not None
        assert result["email"] == "ahmet.yilmaz@acme.com.tr"
        assert result["source"] == "local_guess"
        assert 0 <= result["confidence"] <= 1

    def test_guess_returns_none_when_mx_fails(self):
        api = LeadEnrichmentAPI()
        fake_dns = types.ModuleType("dns")
        fake_resolver = types.ModuleType("dns.resolver")
        fake_resolver.resolve = MagicMock(side_effect=Exception("NXDOMAIN"))
        fake_dns.resolver = fake_resolver

        with patch.dict(sys.modules, {"dns": fake_dns, "dns.resolver": fake_resolver}):
            result = api._guess_email_patterns("A", "B", "nx.invalid")
        assert result is None

    def test_guess_returns_none_on_missing_input(self):
        api = LeadEnrichmentAPI()
        assert api._guess_email_patterns("", "B", "x.com") is None
        assert api._guess_email_patterns("A", "", "x.com") is None
        assert api._guess_email_patterns("A", "B", "") is None


# ─────────────────────────────────────────────────────
# Conditional enrichment gate (EnrichmentPipeline)
# ─────────────────────────────────────────────────────
class TestConditionalGate:
    def _build_pipeline(self):
        db = MagicMock(name="FakeSession")
        with patch.object(pipe_module, "DigitalFootprintScanner"), \
             patch.object(pipe_module, "LeadEnrichmentAPI"):
            return EnrichmentPipeline(db)

    def test_below_threshold_skipped(self):
        pipe = self._build_pipeline()
        lead = SimpleNamespace(id=1, intent_score=42)
        pipe.db.query.return_value.filter.return_value.first.return_value = lead

        with patch.object(pipe_module.settings, "INTENT_SCORE_THRESHOLD_ENRICHMENT", 60):
            result = _run(pipe.enrich_lead(1))

        assert result["status"] == "skipped"
        assert result["reason"] == "below_enrichment_threshold"
        assert result["intent_score"] == 42
        assert result["threshold"] == 60
        # No commit happened — pipeline never reached the body
        pipe.db.commit.assert_not_called()

    def test_at_threshold_runs_pipeline(self):
        pipe = self._build_pipeline()
        lead = SimpleNamespace(
            id=2,
            intent_score=70,
            email=None,
            company_domain="acme.com",
            first_name="A",
            last_name="B",
            social_profiles=[],
            digital_footprint_score=0,
            footprint_scanned_at=None,
            title=None,
            company_name=None,
            technographics={},
            last_4_posts=[],
        )
        pipe.db.query.return_value.filter.return_value.first.return_value = lead

        # Pipeline calls scanner.scan_lead and enrichment_api.full_enrich → mock both
        pipe.scanner.scan_lead = AsyncMock(return_value={
            "profiles": [], "footprint_score": 0.0, "usernames_checked": [], "scan_duration": 0.0
        })
        pipe.enrichment_api.full_enrich = AsyncMock(return_value={
            "email_found": None, "person": {}, "company": {}, "providers_used": [],
        })

        with patch.object(pipe_module.settings, "INTENT_SCORE_THRESHOLD_ENRICHMENT", 60):
            result = _run(pipe.enrich_lead(2))

        # Status should be "success" — gate did NOT short-circuit
        assert result.get("status") != "skipped"

    def test_lead_not_found(self):
        pipe = self._build_pipeline()
        pipe.db.query.return_value.filter.return_value.first.return_value = None
        result = _run(pipe.enrich_lead(999))
        assert result["status"] == "error"
        assert result["reason"] == "lead_not_found"
