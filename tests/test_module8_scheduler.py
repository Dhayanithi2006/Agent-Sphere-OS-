from app.runtime.scheduler import Scheduler


def test_module8_scheduler_prioritizes_and_resumes():
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
