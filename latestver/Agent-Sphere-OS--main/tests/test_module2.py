from fastapi.testclient import TestClient

from main import app


def test_module2_endpoints_and_assignment_flow():
    client = TestClient(app)

    processes = client.get("/processes")
    assert processes.status_code == 200

    assign = client.post(
        "/assign",
        json={"agent": "planner", "task": "Build Todo App"},
    )
    assert assign.status_code == 200
    assert "task_id" in assign.json()

    status = client.get("/supervisor")
    assert status.status_code == 200
    assert status.json()["status"] == "running"
