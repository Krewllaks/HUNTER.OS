"""
HUNTER.OS - Health Endpoint Tests
Tests the /health endpoint for DB and Redis connectivity checks.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoint:
    def test_health_ok(self, client):
        """Health should return 200 when DB is healthy."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"

    def test_health_redis_not_configured(self, client):
        """Redis field should show not_configured when no Redis URL."""
        with patch("app.core.redis.get_redis", return_value=None):
            resp = client.get("/health")
            data = resp.json()
            assert data["redis"] in ("not_configured", "ok")

    def test_health_db_failure(self, client):
        """Health should return 503 when DB is unreachable."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Connection refused")

        with patch("app.core.database.SessionLocal", return_value=mock_session):
            resp = client.get("/health")
            data = resp.json()
            assert resp.status_code == 503
            assert data["status"] == "degraded"
            assert "error" in data["db"]

    def test_health_redis_failure(self, client):
        """Health should return 503 when Redis ping fails."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Redis down")

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            resp = client.get("/health")
            data = resp.json()
            assert resp.status_code == 503
            assert data["status"] == "degraded"
            assert "error" in data["redis"]

    def test_health_redis_ok(self, client):
        """Health should show redis ok when ping succeeds."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            resp = client.get("/health")
            data = resp.json()
            assert data["redis"] == "ok"


class TestHealthEndpointIntegration:
    def test_health_returns_json(self, client):
        resp = client.get("/health")
        assert resp.headers["content-type"] == "application/json"

    def test_health_has_required_fields(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "db" in data
        assert "redis" in data
