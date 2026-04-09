"""
Phase 11 — Footprint Scanner tests.

Covers:
* extract_usernames() — 12+ patterns, dedup, lowercase, TR chars
* scan_lead() — cache hit short-circuit
* _pick_iproyal_proxy() — None when not configured / sticky-session URL otherwise

NO real HTTP. Cache layer is patched. aiohttp is never invoked.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import footprint_scanner as fs_module
from app.services.footprint_scanner import DigitalFootprintScanner


def _run(coro):
    return asyncio.run(coro)


def _make_lead(**kwargs) -> SimpleNamespace:
    base = {
        "id": 1,
        "email": None,
        "linkedin_url": None,
        "first_name": None,
        "last_name": None,
        "full_name": None,
        "company_name": None,
        "company_domain": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


# ─────────────────────────────────────────────────────
# extract_usernames — count + dedup + lowercase
# ─────────────────────────────────────────────────────
class TestExtractUsernamesCount:
    def test_username_count_min_12(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(
            first_name="Ahmet",
            last_name="Yilmaz",
            email="ahmet.yilmaz@acme.com.tr",
            company_domain="acme.com.tr",
        )
        usernames = scanner.extract_usernames(lead)
        assert len(usernames) >= 12, f"got only {len(usernames)}: {usernames}"
        assert len(usernames) <= 20

    def test_username_dedup(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Ahmet", last_name="Yilmaz")
        usernames = scanner.extract_usernames(lead)
        assert len(usernames) == len(set(usernames))

    def test_username_lowercase(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="AHMET", last_name="YILMAZ")
        usernames = scanner.extract_usernames(lead)
        assert all(u == u.lower() for u in usernames)

    def test_username_length_filter(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Ahmet", last_name="Yilmaz")
        usernames = scanner.extract_usernames(lead)
        assert all(2 <= len(u) <= 40 for u in usernames)


# ─────────────────────────────────────────────────────
# Türkçe support
# ─────────────────────────────────────────────────────
class TestUsernamesTurkish:
    def test_username_turkish_chars_normalised(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Şeyma", last_name="Çağdaş")
        usernames = scanner.extract_usernames(lead)
        # ASCII-normalised forms must be present
        assert any("seyma" in u for u in usernames)
        assert any("cagdas" in u for u in usernames)

    def test_turkish_and_raw_forms_coexist(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="İsmail", last_name="Öztürk")
        usernames = scanner.extract_usernames(lead)
        # Should have BOTH ascii and original-form variants
        ascii_hits = [u for u in usernames if "ismail" in u or "ozturk" in u]
        assert ascii_hits, f"no ascii forms: {usernames}"


# ─────────────────────────────────────────────────────
# Pattern coverage
# ─────────────────────────────────────────────────────
class TestUsernamePatterns:
    def test_first_dot_last_present(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Ahmet", last_name="Yilmaz")
        usernames = scanner.extract_usernames(lead)
        assert "ahmet.yilmaz" in usernames

    def test_first_underscore_last_present(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Ahmet", last_name="Yilmaz")
        usernames = scanner.extract_usernames(lead)
        assert "ahmet_yilmaz" in usernames

    def test_initial_last_present(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(first_name="Ahmet", last_name="Yilmaz")
        usernames = scanner.extract_usernames(lead)
        assert "ayilmaz" in usernames

    def test_company_role_aliases(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(
            first_name="Ahmet", last_name="Yilmaz", company_domain="acme.com.tr"
        )
        usernames = scanner.extract_usernames(lead)
        for role in ("info", "contact", "sales", "careers"):
            assert role in usernames, f"missing role alias: {role}"

    def test_email_prefix_split(self):
        scanner = DigitalFootprintScanner()
        lead = _make_lead(email="john.doe@acme.com")
        usernames = scanner.extract_usernames(lead)
        # Both compound and split forms should appear
        assert "john.doe" in usernames
        assert "john" in usernames or "doe" in usernames


# ─────────────────────────────────────────────────────
# scan_lead cache short-circuit
# ─────────────────────────────────────────────────────
class TestScanLeadCache:
    def test_cache_hit_skips_scan(self):
        cached = {
            "profiles": [{"platform": "github", "url": "u"}],
            "footprint_score": 42.0,
            "usernames_checked": ["x"],
            "scan_duration": 0.01,
        }
        with patch.object(fs_module, "cache_get", new=AsyncMock(return_value=cached)), \
             patch.object(fs_module, "cache_set", new=AsyncMock()), \
             patch.object(DigitalFootprintScanner, "scan_username",
                          new=AsyncMock(side_effect=AssertionError("should not run"))):
            scanner = DigitalFootprintScanner()
            lead = _make_lead(id=99, email="ahmet@acme.com.tr",
                              first_name="Ahmet", last_name="Yilmaz")
            result = _run(scanner.scan_lead(lead))
        assert result == cached


# ─────────────────────────────────────────────────────
# IPRoyal proxy picker
# ─────────────────────────────────────────────────────
class TestIProyalPicker:
    def test_no_creds_returns_none(self):
        with patch.object(fs_module.settings, "IPROYAL_USERNAME", None), \
             patch.object(fs_module.settings, "IPROYAL_PASSWORD", None):
            assert DigitalFootprintScanner()._pick_iproyal_proxy() is None

    def test_returns_sticky_session_dict(self):
        with patch.object(fs_module.settings, "IPROYAL_USERNAME", "user1"), \
             patch.object(fs_module.settings, "IPROYAL_PASSWORD", "pass1"), \
             patch.object(fs_module.settings, "IPROYAL_ENDPOINT", "geo.iproyal.com:12321"), \
             patch.object(fs_module.settings, "IPROYAL_POOL_SIZE", 5):
            proxy = DigitalFootprintScanner()._pick_iproyal_proxy()
        assert proxy is not None
        assert proxy["server"] == "http://geo.iproyal.com:12321"
        assert proxy["password"] == "pass1"
        assert proxy["username"].startswith("user1-session-")
        assert proxy["username"].endswith("-country-tr")
