from app.checkpoint.checkpoint_manager import CheckpointManager
from app.events.event_bus import EventBus
from app.events.event_types import EVENT_AGENT_FAILED, EVENT_AGENT_FINISHED, EVENT_AGENT_STARTED, EVENT_CHECKPOINT_SAVED, EVENT_MEMORY_UPDATED, EVENT_RECOVERY_COMPLETED, EVENT_ROLLBACK_TRIGGERED
from app.runtime.recovery import RecoveryEngine
from app.runtime.scheduler import Scheduler


def test_checkpoint_manager_persists_versions_and_restores():
    manager = CheckpointManager(db_path=':memory:')
    cp1 = manager.save_checkpoint('planner', {'state': 'created'})
    cp2 = manager.save_checkpoint('planner', {'state': 'running'})

    restored = manager.restore(cp2.checkpoint_id)
    assert restored['state'] == 'running'
    assert manager.get_versions('planner') == [cp1.checkpoint_id, cp2.checkpoint_id]
    assert manager.get_latest('planner').checkpoint_id == cp2.checkpoint_id


def test_recovery_engine_selectively_recovers_affected_agents():
    dependency_manager = type('Deps', (), {'get_affected_agents': lambda self, failed_agent_id: {'planner', 'developer'}})()
    checkpoint_manager = CheckpointManager(db_path=':memory:')
    recovery_engine = RecoveryEngine(dependency_manager=dependency_manager, checkpoint_manager=checkpoint_manager)

    checkpoint_id = recovery_engine.create_checkpoint('planner', {'state': 'ok'})
    plan = recovery_engine.plan_recovery('research')
    restored = recovery_engine.restore_checkpoint(checkpoint_id)

    assert plan == ['developer', 'planner']
    assert restored == {'state': 'ok'}
    assert recovery_engine.recover('research', {'state': 'restored'}) == ['developer', 'planner']


def test_scheduler_supports_priority_fifo_and_resume():
    scheduler = Scheduler()
    scheduler.enqueue('first', priority=2)
    scheduler.enqueue('second', priority=1)
    scheduler.enqueue('third', priority=1)

    assert scheduler.dequeue() == 'second'
    assert scheduler.dequeue() == 'third'
    assert scheduler.dequeue() == 'first'

    scheduler.pause('first')
    assert scheduler.is_paused('first') is True
    scheduler.resume('first')
    assert scheduler.is_paused('first') is False


def test_event_bus_publishes_and_broadcasts():
    event_bus = EventBus()
    events = []
    event_bus.subscribe(EVENT_AGENT_STARTED, lambda payload: events.append(('start', payload)))
    event_bus.subscribe(EVENT_AGENT_FINISHED, lambda payload: events.append(('finish', payload)))
    event_bus.publish(EVENT_AGENT_STARTED, {'agent': 'planner'})
    event_bus.publish(EVENT_AGENT_FINISHED, {'agent': 'planner'})

    assert events == [('start', {'agent': 'planner'}), ('finish', {'agent': 'planner'})]
