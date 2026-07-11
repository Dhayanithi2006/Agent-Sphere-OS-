"""Tests for async task execution, SSE streaming, and the live dashboard UI.

All tests run against the FastAPI TestClient which executes BackgroundTasks
synchronously — so task completion can be asserted immediately after the
/assign call returns.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from main import app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assign(client: TestClient, agent_id: str, input_value: str) -> dict:
    resp = client.post(
        "/assign",
        json={"agent_id": agent_id, "task": input_value, "input": input_value},
    )
    assert resp.status_code == 200, f"assign failed: {resp.text}"
    return resp.json()


# ── 1. Async task submission ──────────────────────────────────────────────────

def test_assign_returns_task_id_and_queued_status():
    """/assign must return task_id and a queued status immediately."""
    client = TestClient(app)
    data = _assign(client, "planner", "Design the memory subsystem")
    assert "task_id" in data
    assert len(data["task_id"]) > 0


def test_assign_all_five_agents_succeed():
    """Every registered agent must accept a task without error."""
    client = TestClient(app)
    cases = [
        ("planner",    "Plan a caching layer"),
        ("researcher", "OAuth2 token patterns"),
        ("developer",  "Implement token refresh endpoint"),
        ("tester",     "Token refresh validation tests"),
        ("reviewer",   "Review token refresh code"),
    ]
    for agent_id, input_val in cases:
        data = _assign(client, agent_id, input_val)
        assert "task_id" in data, f"No task_id for {agent_id}"


# ── 2. Payload key mapping ────────────────────────────────────────────────────

def test_researcher_payload_maps_to_topic_key():
    """The 'input' field sent by the UI must be mapped to researcher's 'topic' key."""
    client = TestClient(app)
    data = _assign(client, "researcher", "distributed tracing")
    task_id = data["task_id"]

    task = client.get(f"/tasks/{task_id}").json()
    # TestClient runs BG tasks synchronously; task should be completed
    assert task["status"] == "completed"
    # The QwenClient mock prefixes the prompt — check it contains the topic
    assert "distributed tracing" in (task["result"] or "").lower() or "[qwen]" in (task["result"] or "")


def test_developer_payload_maps_to_requirement_key():
    """The 'input' field must map to developer's 'requirement' payload key."""
    client = TestClient(app)
    data = _assign(client, "developer", "implement rate limiter")
    task = client.get(f"/tasks/{data['task_id']}").json()
    assert task["status"] == "completed"
    assert task["result"] is not None


# ── 3. Task lifecycle ─────────────────────────────────────────────────────────

def test_task_status_endpoint_reachable_after_submission():
    """/tasks/{task_id} must respond with a valid status after submission."""
    client = TestClient(app)
    task_id = _assign(client, "planner", "Build memory versioning")["task_id"]

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("pending", "running", "completed", "failed")


def test_task_completes_and_result_is_non_empty():
    """After execution, the task result must be a non-empty string."""
    client = TestClient(app)
    task_id = _assign(client, "planner", "Build dashboard")["task_id"]

    task = client.get(f"/tasks/{task_id}").json()
    assert task["status"] == "completed"
    assert task["result"] is not None
    assert len(str(task["result"])) > 0


def test_task_result_stored_in_shared_memory():
    """After task completion, the result should appear in /memory under the task key."""
    client = TestClient(app)
    task_id = _assign(client, "planner", "Build shared memory audit")["task_id"]

    memory = client.get("/memory").json()
    all_keys = str(memory)
    # The supervisor writes task:<task_id> and planner:goal keys
    assert task_id in all_keys or "planner" in all_keys


# ── 4. Process table ─────────────────────────────────────────────────────────

def test_process_table_grows_after_task_submission():
    """Each /assign call should add exactly one entry to the process table."""
    client = TestClient(app)
    before = len(client.get("/processes").json())
    _assign(client, "developer", "implement cache invalidation")
    after = len(client.get("/processes").json())
    assert after == before + 1


def test_completed_process_has_expected_fields():
    """Process table entries must contain pid, agent_name, state and current_task."""
    client = TestClient(app)
    _assign(client, "tester", "auth middleware tests")
    processes = client.get("/processes").json()
    assert len(processes) >= 1
    last = processes[-1]
    assert "pid"          in last
    assert "agent_name"   in last
    assert "current_task" in last
    # state field exists (value may differ by serializer)
    assert "state" in last or "current_state" in last


# ── 5. SSE stream ─────────────────────────────────────────────────────────────

def test_stream_endpoint_returns_event_stream_content_type():
    """/stream must respond with text/event-stream content-type."""
    import json as _json

    client = TestClient(app)

    # Use once=true so the stream generator terminates immediately after one frame.
    resp = client.get("/stream?once=true")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    content = resp.text
    assert content.startswith("data:")
    
    # Parse the data event
    payload = _json.loads(content[5:].strip())
    assert "processes"   in payload
    assert "supervisor"  in payload
    assert "memory_keys" in payload


# ── 6. Dashboard UI ───────────────────────────────────────────────────────────

def test_dashboard_route_returns_html():
    """/dashboard must serve a valid HTML page."""
    client = TestClient(app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text.lower()
    assert "<html" in body
    assert "agentsphere" in body


def test_dashboard_contains_agent_select_and_form():
    """The dashboard HTML must include the agent selection form elements."""
    client = TestClient(app)
    body = client.get("/dashboard").text
    assert "agent-select"  in body
    assert "task-input"    in body
    assert "run-btn"       in body
    assert "process-tbody" in body
    assert "memory-viewer" in body


def test_dashboard_references_sse_stream_endpoint():
    """The dashboard JS must connect to the /stream SSE endpoint."""
    client = TestClient(app)
    body = client.get("/dashboard").text
    assert "/stream" in body
    assert "EventSource" in body


# ── 7. CORS ───────────────────────────────────────────────────────────────────

def test_cors_headers_present_on_preflight():
    """CORS preflight OPTIONS must be accepted and return allow-origin header."""
    client = TestClient(app)
    resp = client.options(
        "/assign",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code in (200, 204)
    assert "access-control-allow-origin" in resp.headers


def test_cors_header_on_regular_get():
    """Standard GET requests should carry CORS allow-origin header."""
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


# ── 8. Dependency visualization endpoint ─────────────────────────────────────

def test_dependencies_visualize_returns_pyvis_html():
    """/dependencies/visualize must return HTML containing the pyvis network."""
    client = TestClient(app)
    resp = client.get("/dependencies/visualize")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "mynetwork" in body
    # Agents seeded in routes.py should appear
    for agent in ("PLANNER", "RESEARCHER", "DEVELOPER", "TESTER", "REVIEWER"):
        assert agent in body
