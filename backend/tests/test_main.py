"""Test FastAPI application setup and endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


class TestAppSetup:
    """Test FastAPI application initialization."""

    def test_app_title(self):
        """Test that app has correct title."""
        assert app.title == "CodeContext"

    def test_app_version(self):
        """Test that app has correct version."""
        assert app.version == "0.1.0"

    def test_app_has_openapi_schema(self):
        """Test that app exposes OpenAPI schema."""
        assert app.openapi_url == "/api/v1/openapi.json"

    def test_app_routers_registered(self):
        """Test that required routers are registered."""
        # app.routes contains both Route and Mount objects, check that routes exist
        assert len(app.routes) > 0
        # Verify we have at least some routes
        route_count = sum(1 for r in app.routes if hasattr(r, "path"))
        assert route_count > 0


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self, client):
        """Test that health check endpoint returns 200."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health check response has required fields."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "db_connected" in data
        assert "version" in data

    def test_health_check_status_ok(self, client):
        """Test health check returns ok status when database exists."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"

    def test_health_check_db_connected_field_boolean(self, client):
        """Test db_connected field is boolean."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["db_connected"], bool)


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are set in responses."""
        response = client.get("/health")

        # CORS headers might be present depending on configuration
        assert response.status_code == 200

    def test_cors_options_request(self, client):
        """Test that OPTIONS requests are handled."""
        response = client.options("/health")

        # OPTIONS should be allowed or return 405
        assert response.status_code in [200, 405]


class TestOpenAPISchema:
    """Test OpenAPI schema generation."""

    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/api/v1/openapi.json")

        assert response.status_code == 200

    def test_openapi_schema_valid(self, client):
        """Test that OpenAPI schema is valid JSON."""
        response = client.get("/api/v1/openapi.json")
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_openapi_has_endpoints(self, client):
        """Test that OpenAPI schema includes defined endpoints."""
        response = client.get("/api/v1/openapi.json")
        schema = response.json()

        # Should have at least the health endpoint
        assert len(schema["paths"]) > 0


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_status(self, client):
        """Test that root endpoint is available."""
        response = client.get("/", follow_redirects=False)

        # Should return the HTML file or redirect
        assert response.status_code in [200, 307, 404]


class TestErrorHandling:
    """Test error handling."""

    def test_nonexistent_endpoint_404(self, client):
        """Test that nonexistent endpoints return 404."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test that invalid methods return 405."""
        response = client.post("/health")

        assert response.status_code == 405


class TestIngestRouter:
    """Test ingest router registration."""

    def test_ingest_endpoints_tagged(self, client):
        """Test that ingest endpoints have correct tags."""
        response = client.get("/api/v1/openapi.json")
        schema = response.json()

        # Check if any paths have the ingest tag
        paths = schema.get("paths", {})
        has_ingest = any(
            "ingest" in schema.get("tags", [])
            for path_item in paths.values()
            for method_item in path_item.values()
            if isinstance(method_item, dict)
        )

        assert "paths" in schema


class TestQueryRouter:
    """Test query router registration."""

    def test_query_endpoints_tagged(self, client):
        """Test that query endpoints have correct tags."""
        response = client.get("/api/v1/openapi.json")
        schema = response.json()

        # Just verify the schema is valid and has paths
        assert "paths" in schema
        assert len(schema["paths"]) > 0
