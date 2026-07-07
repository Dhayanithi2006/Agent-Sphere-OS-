from app.memory.shared_memory import SharedMemory


def test_module3_memory_round_trip():
    memory = SharedMemory(db_path=':memory:')
    memory.set('key', {'value': 42})
    assert memory.get('key')['value'] == 42
    assert memory.exists('key') is True
