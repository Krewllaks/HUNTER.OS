"""
HUNTER.OS - Comprehensive Auth API Tests
Integration Tests — duvar (wall) level
AAA Pattern | Edge Cases | Error Scenarios
"""
import pytest


class TestRegister:
    """User registration endpoint tests."""

    def test_register_happy_path(self, client):
        """Valid registration should return 201 with user data."""
        # ARRANGE
        payload = {
            "email": "newuser@company.com",
            "password": "strongPass123!",
            "full_name": "New User",
        }

        # ACT
        res = client.post("/api/v1/auth/register", json=payload)

        # ASSERT
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "newuser@company.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # Password should NEVER leak

    def test_register_duplicate_email(self, client, test_user):
        """Duplicate email should return 400."""
        res = client.post("/api/v1/auth/register", json={
            "email": "test@hunter.os",  # Already exists from test_user fixture
            "password": "pass123",
            "full_name": "Duplicate",
        })
        assert res.status_code == 400

    # ── Edge Cases ──────────────────────────────────────
    def test_register_empty_email(self, client):
        """Empty email should fail validation."""
        res = client.post("/api/v1/auth/register", json={
            "email": "",
            "password": "pass123",
            "full_name": "NoEmail",
        })
        assert res.status_code == 422  # Pydantic validation

    def test_register_invalid_email_format(self, client):
        """Invalid email format should fail."""
        res = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "pass123",
            "full_name": "BadEmail",
        })
        assert res.status_code == 422

    def test_register_missing_password(self, client):
        """Missing password field should fail."""
        res = client.post("/api/v1/auth/register", json={
            "email": "test@test.com",
            "full_name": "NoPass",
        })
        assert res.status_code == 422

    def test_register_missing_full_name(self, client):
        """Missing full_name field should fail."""
        res = client.post("/api/v1/auth/register", json={
            "email": "test@test.com",
            "password": "pass123",
        })
        assert res.status_code == 422

    def test_register_empty_body(self, client):
        """Empty request body should fail."""
        res = client.post("/api/v1/auth/register", json={})
        assert res.status_code == 422

    def test_register_turkish_characters_in_name(self, client):
        """Turkish characters in full_name should work."""
        res = client.post("/api/v1/auth/register", json={
            "email": "turk@test.com",
            "password": "pass123",
            "full_name": "Çağdaş Öztürk",
        })
        assert res.status_code == 201
        assert res.json()["full_name"] == "Çağdaş Öztürk"

    def test_register_default_plan_is_trial(self, client):
        """New user should default to trial plan."""
        res = client.post("/api/v1/auth/register", json={
            "email": "plancheck@test.com",
            "password": "pass123",
            "full_name": "Plan Check",
        })
        assert res.status_code == 201
        # Plan should be trial by default
        data = res.json()
        assert data.get("plan", "trial") == "trial"


class TestLogin:
    """User login endpoint tests."""

    def test_login_happy_path(self, client, test_user):
        """Valid credentials should return access token."""
        # ARRANGE & ACT
        res = client.post("/api/v1/auth/login", data={
            "username": "test@hunter.os",
            "password": "testpass123",
        })

        # ASSERT
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Wrong password should return 401."""
        res = client.post("/api/v1/auth/login", data={
            "username": "test@hunter.os",
            "password": "definitely-wrong",
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Non-existent email should return 401."""
        res = client.post("/api/v1/auth/login", data={
            "username": "ghost@nowhere.com",
            "password": "pass123",
        })
        assert res.status_code == 401

    def test_login_empty_credentials(self, client):
        """Empty credentials should fail."""
        res = client.post("/api/v1/auth/login", data={
            "username": "",
            "password": "",
        })
        assert res.status_code in [401, 422]

    def test_login_case_sensitivity(self, client, test_user):
        """Email should be case-insensitive or exact match."""
        # Test with uppercase — behavior depends on implementation
        res = client.post("/api/v1/auth/login", data={
            "username": "TEST@HUNTER.OS",
            "password": "testpass123",
        })
        # Either 200 (case insensitive) or 401 (case sensitive) is valid
        assert res.status_code in [200, 401]

    def test_login_returns_valid_jwt(self, client, test_user):
        """Token from login should be usable for authenticated endpoints."""
        # ARRANGE: Login
        login_res = client.post("/api/v1/auth/login", data={
            "username": "test@hunter.os",
            "password": "testpass123",
        })
        token = login_res.json()["access_token"]

        # ACT: Use token
        me_res = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })

        # ASSERT
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "test@hunter.os"


class TestProtectedEndpoints:
    """Test authentication guards on protected routes."""

    def test_me_with_valid_token(self, client, auth_headers):
        """Valid token should return user data."""
        res = client.get("/api/v1/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "email" in data
        assert "full_name" in data
        assert "id" in data

    def test_me_without_token(self, client):
        """No token should return 401."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_me_with_invalid_token(self, client):
        """Invalid token should return 401."""
        res = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer totally-invalid-token"
        })
        assert res.status_code == 401

    def test_me_with_expired_token(self, client):
        """Expired token should return 401."""
        from app.core.security import create_access_token
        from datetime import timedelta
        token = create_access_token(subject="1", expires_delta=timedelta(seconds=-10))
        res = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 401

    def test_products_without_auth(self, client):
        """Products endpoint without auth should return 401."""
        res = client.get("/api/v1/products")
        assert res.status_code == 401

    def test_leads_without_auth(self, client):
        """Leads endpoint without auth should return 401."""
        res = client.get("/api/v1/leads")
        assert res.status_code == 401

    def test_analytics_without_auth(self, client):
        """Analytics endpoint without auth should return 401."""
        res = client.get("/api/v1/analytics/dashboard")
        assert res.status_code == 401
