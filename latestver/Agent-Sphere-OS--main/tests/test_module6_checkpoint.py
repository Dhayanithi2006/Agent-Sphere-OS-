from app.checkpoint.checkpoint_manager import CheckpointManager


def test_module6_checkpoint_manager_versions_and_restores():
    manager = CheckpointManager(db_path=':memory:')
    first = manager.save_checkpoint('planner', {'state': 'created'})
    second = manager.save_checkpoint('planner', {'state': 'running'})

    assert manager.get_versions('planner') == [first.checkpoint_id, second.checkpoint_id]
    assert manager.restore(second.checkpoint_id)['state'] == 'running'
