from app.memory.shared_memory import SharedMemory


def test_shared_memory_write_read_and_history():
    memory = SharedMemory(db_path="/tmp/agent_sphere_module3.sqlite")
    memory.clear()

    memory.write(namespace="planner", key="goal", value="Build Todo App")
    assert memory.read(namespace="planner", key="goal") == "Build Todo App"

    history = memory.history(namespace="planner", key="goal")
    assert len(history) >= 1
