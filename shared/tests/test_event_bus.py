from unittest import TestCase

from shared.domain.event import DomainEvent
from shared.infrastructure import event_bus


class _EventA(DomainEvent):
    pass


class _EventB(DomainEvent):
    pass


class EventBusTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(event_bus.isolated_subscribers())

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

    def test_unsubscribe_stops_handler_from_being_called(self) -> None:
        received: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received.append)

        event_bus.unsubscribe(_EventA, received.append)
        event_bus.publish([_EventA()])

        self.assertEqual(received, [])

    def test_unsubscribe_leaves_other_handlers_untouched(self) -> None:
        received_1: list[DomainEvent] = []
        received_2: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received_1.append)
        event_bus.subscribe(_EventA, received_2.append)

        event_bus.unsubscribe(_EventA, received_1.append)
        event = _EventA()
        event_bus.publish([event])

        self.assertEqual(received_1, [])
        self.assertEqual(received_2, [event])

    def test_unsubscribe_unknown_handler_is_a_no_op(self) -> None:
        def handler(event: DomainEvent) -> None:
            pass

        event_bus.unsubscribe(_EventA, handler)  # should not raise


class IsolatedSubscribersTests(TestCase):
    def test_subscribers_outside_are_hidden_inside_and_restored_on_exit(self) -> None:
        received: list[DomainEvent] = []
        event_bus.subscribe(_EventA, received.append)
        self.addCleanup(event_bus.unsubscribe, _EventA, received.append)

        with event_bus.isolated_subscribers():
            event_bus.publish([_EventA()])
        self.assertEqual(received, [])

        event = _EventA()
        event_bus.publish([event])
        self.assertEqual(received, [event])

    def test_subscriptions_made_inside_are_dropped_on_exit(self) -> None:
        received: list[DomainEvent] = []

        with event_bus.isolated_subscribers():
            event_bus.subscribe(_EventA, received.append)

        event_bus.publish([_EventA()])
        self.assertEqual(received, [])
