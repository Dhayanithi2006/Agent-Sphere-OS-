from app.events.event_bus import EventBus
from app.events.event_types import EVENT_AGENT_STARTED, EVENT_AGENT_FINISHED


def test_module9_event_bus_publish_and_subscribe():
    event_bus = EventBus()
    events = []
    event_bus.subscribe(EVENT_AGENT_STARTED, lambda payload: events.append(('start', payload)))
    event_bus.subscribe(EVENT_AGENT_FINISHED, lambda payload: events.append(('finish', payload)))

    event_bus.publish(EVENT_AGENT_STARTED, {'agent': 'planner'})
    event_bus.publish(EVENT_AGENT_FINISHED, {'agent': 'planner'})

    assert events == [('start', {'agent': 'planner'}), ('finish', {'agent': 'planner'})]
