from app.checkpoint.checkpoint_manager import CheckpointManager
from app.dependency.dependency_manager import DependencyManager
from app.runtime.recovery import RecoveryEngine


def test_module7_recovery_engine_plans_and_recovers():
    dependency_manager = DependencyManager()
    dependency_manager.add_dependency('planner', 'research')
    dependency_manager.add_dependency('developer', 'planner')
    recovery_engine = RecoveryEngine(dependency_manager=dependency_manager, checkpoint_manager=CheckpointManager(db_path=':memory:'))

    checkpoint_id = recovery_engine.create_checkpoint('planner', {'state': 'ok'})
    assert recovery_engine.plan_recovery('research') == ['developer', 'planner']
    assert recovery_engine.restore_checkpoint(checkpoint_id) == {'state': 'ok'}
    assert recovery_engine.recover('research', {'state': 'restored'}) == ['developer', 'planner']
