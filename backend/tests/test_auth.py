"""
HUNTER.OS - Auth API Tests
"""
import pytest


class TestAuth:
    def test_register(self, client):
        """Test user registration."""
        res = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "securePass123",
            "full_name": "New User",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "new@test.com"

    def test_register_duplicate(self, client, test_user):
        """Test duplicate registration fails."""
        res = client.post("/api/v1/auth/register", json={
            "email": "test@hunter.os",
            "password": "pass123",
            "full_name": "Dup User",
        })
        assert res.status_code == 400

    def test_login(self, client, test_user):
        """Test login returns access token."""
        res = client.post("/api/v1/auth/login", data={
            "username": "test@hunter.os",
            "password": "testpass123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails."""
        res = client.post("/api/v1/auth/login", data={
            "username": "test@hunter.os",
            "password": "wrongpass",
        })
        assert res.status_code == 401

    def test_me(self, client, auth_headers):
        """Test /auth/me returns current user."""
        res = client.get("/api/v1/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "test@hunter.os"

    def test_me_no_token(self, client):
        """Test /auth/me without token fails."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
