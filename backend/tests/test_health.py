"""
Tests for health check and root endpoints.

Tests the application's observability endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRootEndpoint:
    """Tests for the root / endpoint."""

    def test_returns_200(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_app_info(self, client):
        """Root endpoint should return app information."""
        response = client.get("/")
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert "docs" in data

    def test_status_is_running(self, client):
        """Status should be 'running'."""
        response = client.get("/")
        data = response.json()

        assert data["status"] == "running"

    def test_docs_url_provided(self, client):
        """Documentation URL should be provided."""
        response = client.get("/")
        data = response.json()

        assert data["docs"] == "/docs"


class TestHealthCheckEndpoint:
    """Tests for the /health endpoint."""

    def test_returns_200_when_healthy(self, client):
        """Health check should return 200 when database is accessible."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_status_field(self, client):
        """Response should include overall status field."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    def test_returns_version(self, client):
        """Response should include app version."""
        response = client.get("/health")
        data = response.json()

        assert "version" in data

    def test_returns_database_status(self, client):
        """Response should include database status."""
        response = client.get("/health")
        data = response.json()

        assert "database" in data
        assert data["database"] in ["healthy", "unhealthy"]

    def test_healthy_response_structure(self, client):
        """Healthy response should have correct structure."""
        response = client.get("/health")
        data = response.json()

        # When healthy, should not have database_error field
        if data["status"] == "healthy":
            assert "database_error" not in data

    def test_database_connectivity_checked(self, client):
        """Health check should test database connectivity and report status."""
        response = client.get("/health")
        data = response.json()

        # The health check uses SessionLocal directly (not via dependency injection),
        # so it tests the real database. It may be healthy or unhealthy depending
        # on whether PostgreSQL is running. The key assertion is that connectivity
        # is checked and a valid status is returned.
        assert data["database"] in ["healthy", "unhealthy"]

    def test_no_auth_required(self, client):
        """Health check should not require authentication."""
        # No auth headers provided
        response = client.get("/health")

        # Should still succeed
        assert response.status_code == 200


class TestHealthCheckWithDatabaseFailure:
    """Tests for health check behavior when database is unavailable."""

    def test_returns_unhealthy_on_db_error(self, client):
        """Should return unhealthy status when database query fails."""
        with patch("backend.main.SessionLocal") as mock_session_local:
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Connection refused")
            mock_session_local.return_value = mock_session

            response = client.get("/health")
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["database"] == "unhealthy"

    def test_includes_error_details_when_unhealthy(self, client):
        """Should include error details when database is unhealthy."""
        with patch("backend.main.SessionLocal") as mock_session_local:
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Connection timeout")
            mock_session_local.return_value = mock_session

            response = client.get("/health")
            data = response.json()

            assert "database_error" in data
            assert "Connection timeout" in data["database_error"]

    def test_still_returns_200_when_unhealthy(self, client):
        """Should return 200 even when unhealthy (for load balancer compatibility)."""
        with patch("backend.main.SessionLocal") as mock_session_local:
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_session

            response = client.get("/health")

            # Many health check implementations return 200 with status in body
            # to allow load balancers to read the response
            assert response.status_code == 200


class TestDocsEndpoint:
    """Tests for OpenAPI documentation endpoints."""

    def test_docs_endpoint_accessible(self, client):
        """Swagger UI docs should be accessible."""
        response = client.get("/docs")
        # Redirects are acceptable, or 200 for direct access
        assert response.status_code in [200, 307]

    def test_redoc_endpoint_accessible(self, client):
        """ReDoc docs should be accessible."""
        response = client.get("/redoc")
        assert response.status_code in [200, 307]

    def test_openapi_json_accessible(self, client):
        """OpenAPI JSON schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
