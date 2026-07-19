"""Unit and integration tests for Module 16 (Dashboard Backend)."""

from __future__ import annotations

from typing import Any
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def test_client() -> TestClient:
    """Fixture providing a fresh FastAPI TestClient instance."""
    return TestClient(app)


def test_dashboard_metrics_endpoint(test_client):
    """Verify GET /api/dashboard/metrics returns CPU/RAM and supervisor task/process stats."""
    response = test_client.get("/api/dashboard/metrics")
    assert response.status_code == 200
    
    data = response.json()
    assert "system" in data
    assert "cpu_percent" in data["system"]
    assert "memory" in data["system"]
    assert "disk" in data["system"]
    
    assert "tasks" in data
    assert "total" in data["tasks"]
    assert "running" in data["tasks"]
    
    assert "processes" in data
    assert "total" in data["processes"]
    assert "active" in data["processes"]


def test_dashboard_dependency_graph_endpoint(test_client):
    """Verify GET /api/dashboard/dependency-graph returns nodes, edges, cycle, and sorting info."""
    response = test_client.get("/api/dashboard/dependency-graph")
    assert response.status_code == 200
    
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "has_cycle" in data
    assert "topological_order" in data
    
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_dashboard_executions_endpoint(test_client):
    """Verify GET /api/dashboard/executions returns execution history lists and general stats."""
    response = test_client.get("/api/dashboard/executions")
    assert response.status_code == 200
    
    data = response.json()
    assert "metrics" in data
    assert "history" in data
    
    assert "total_executions" in data["metrics"]
    assert "success_count" in data["metrics"]
    assert isinstance(data["history"], list)


def test_dashboard_token_cost_endpoint(test_client):
    """Verify GET /api/dashboard/token-cost returns router model billing and token counts."""
    response = test_client.get("/api/dashboard/token-cost")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_calls" in data
    assert "total_prompt_tokens" in data
    assert "total_completion_tokens" in data
    assert "total_cost" in data


def test_dashboard_checkpoints_endpoint(test_client):
    """Verify GET /api/dashboard/checkpoints lists saved checkpoint indices."""
    response = test_client.get("/api/dashboard/checkpoints")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "task_id" in data[0]
        assert "state_size_bytes" in data[0]


def test_dashboard_websocket_stream(test_client):
    """Verify WebSocket /api/dashboard/ws accepts connections and streams json payloads."""
    with test_client.websocket_connect("/api/dashboard/ws") as websocket:
        # Receive first frame
        payload = websocket.receive_json()
        
        assert payload["type"] == "dashboard_update"
        assert "system" in payload
        assert "processes" in payload
        assert "llm_usage" in payload
        assert "events" in payload
        
        assert "cpu_percent" in payload["system"]
        assert isinstance(payload["processes"], list)
        assert isinstance(payload["events"], list)
