"""Unit and integration tests for Module 17 (React Dashboard rendering)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def test_client() -> TestClient:
    """Fixture providing a fresh FastAPI TestClient instance."""
    return TestClient(app)


def test_dashboard_page_serves_html_and_assets(test_client):
    """Verify GET /dashboard returns the customized HTML React SPA page."""
    response = test_client.get("/dashboard")
    assert response.status_code == 200
    
    html_content = response.text
    # Verify standard HTML document headers
    assert "<!DOCTYPE html>" in html_content
    assert "AgentSphere OS" in html_content
    
    # Verify Tailwind, React, and Babel dependencies exist
    assert "tailwindcss.com" in html_content
    assert "react@18" in html_content
    assert "babel.min.js" in html_content
    
    # Verify DOM mounting anchor target
    assert '<div id="root"' in html_content
