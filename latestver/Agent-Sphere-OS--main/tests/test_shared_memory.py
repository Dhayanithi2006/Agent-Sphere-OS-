import os
import sqlite3
import tempfile

from app.memory.shared_memory import SharedMemory


def test_shared_memory_supports_crud_and_snapshots():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "shared_memory.sqlite")
        memory = SharedMemory(db_path=db_path)

        memory.set("greeting", {"value": "hello"})
        assert memory.get("greeting")["value"] == "hello"
        assert memory.exists("greeting") is True

        memory.update("greeting", {"value": "updated"})
        assert memory.get("greeting")["value"] == "updated"

        snapshot = memory.snapshot()
        assert snapshot["greeting"]["value"] == "updated"

        memory.delete("greeting")
        assert memory.exists("greeting") is False


def test_shared_memory_persists_versions_and_reloads():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "shared_memory.sqlite")
        memory = SharedMemory(db_path=db_path)
        memory.set("count", 1)
        memory.update("count", 2)
        version_history = memory.version_history("count")

        assert len(version_history) >= 2
        assert version_history[0]["value"] == 1
        assert version_history[-1]["value"] == 2

        reloaded = SharedMemory(db_path=db_path)
        assert reloaded.get("count") == 2


def test_shared_memory_is_thread_safe_for_concurrent_writes():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "shared_memory.sqlite")
        memory = SharedMemory(db_path=db_path)

        import threading

        def writer(key: str, value: int) -> None:
            for _ in range(5):
                memory.set(key, value)

        threads = [threading.Thread(target=writer, args=("shared", index)) for index in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert memory.get("shared") in {0, 1, 2}
