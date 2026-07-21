from unittest import TestCase

from shared.domain.event import DomainEvent
from shared.infrastructure import event_bus


class _EventA(DomainEvent):
    pass


class _EventB(DomainEvent):
    pass


class EventBusTests(TestCase):
    def setUp(self) -> None:
        event_bus.clear_subscribers()
        self.addCleanup(event_bus.clear_subscribers)

    def test_publish_calls_subscribed_handler(self) -> None:
        received: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received.append)

        event = _EventA()
        event_bus.publish([event])

        self.assertEqual(received, [event])

    def test_publish_does_not_call_handler_for_other_event_type(self) -> None:
        received: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received.append)

        event_bus.publish([_EventB()])

        self.assertEqual(received, [])

    def test_multiple_handlers_are_all_called(self) -> None:
        received_1: list[DomainEvent] = []
        received_2: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received_1.append)
        event_bus.subscribe(_EventA, received_2.append)

        event = _EventA()
        event_bus.publish([event])

        self.assertEqual(received_1, [event])
        self.assertEqual(received_2, [event])

    def test_handler_exception_propagates(self) -> None:
        def failing_handler(event: DomainEvent) -> None:
            raise ValueError("boom")

        event_bus.subscribe(_EventA, failing_handler)

        with self.assertRaises(ValueError):
            event_bus.publish([_EventA()])
