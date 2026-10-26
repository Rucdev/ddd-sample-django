import uuid
from unittest import TestCase

from kitchen.domain.entities import Ticket
from kitchen.domain.events import CookingCompleted, CookingStarted
from kitchen.domain.exceptions import InvalidTicketTransition
from kitchen.domain.value_objects import TicketItem, TicketStatus


def _make_ticket() -> Ticket:
    return Ticket.open(order_id=uuid.uuid4(), items=[TicketItem(name="カフェラテ", quantity=2)])


class TicketTests(TestCase):
    def test_open_starts_queued_without_events(self) -> None:
        ticket = _make_ticket()

        self.assertEqual(ticket.status, TicketStatus.QUEUED)
        self.assertEqual(ticket.collect_events(), [])

    def test_start_cooking_records_event(self) -> None:
        ticket = _make_ticket()

        ticket.start_cooking()

        self.assertEqual(ticket.status, TicketStatus.COOKING)
        events = ticket.collect_events()
        self.assertEqual(len(events), 1)
        event = events[0]
        assert isinstance(event, CookingStarted)
        self.assertEqual(event.order_id, ticket.order_id)

    def test_complete_records_event(self) -> None:
        ticket = _make_ticket()
        ticket.start_cooking()
        ticket.collect_events()

        ticket.complete()

        self.assertEqual(ticket.status, TicketStatus.DONE)
        self.assertIsInstance(ticket.collect_events()[0], CookingCompleted)

    def test_cannot_complete_before_cooking(self) -> None:
        with self.assertRaises(InvalidTicketTransition):
            _make_ticket().complete()

    def test_cannot_start_cooking_twice(self) -> None:
        ticket = _make_ticket()
        ticket.start_cooking()

        with self.assertRaises(InvalidTicketTransition):
            ticket.start_cooking()

    def test_cancel_queued_ticket(self) -> None:
        ticket = _make_ticket()

        ticket.cancel()

        self.assertEqual(ticket.status, TicketStatus.CANCELLED)

    def test_cannot_cancel_while_cooking(self) -> None:
        ticket = _make_ticket()
        ticket.start_cooking()

        with self.assertRaises(InvalidTicketTransition):
            ticket.cancel()

    def test_cancelled_ticket_cannot_start_cooking(self) -> None:
        ticket = _make_ticket()
        ticket.cancel()

        with self.assertRaises(InvalidTicketTransition):
            ticket.start_cooking()
