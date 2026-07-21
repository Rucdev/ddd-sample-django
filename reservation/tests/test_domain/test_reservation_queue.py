import uuid
from datetime import date, timedelta
from unittest import TestCase

from reservation.domain.entities import ReservationQueue
from reservation.domain.events import HoldExpired, HoldReady
from reservation.domain.exceptions import DuplicateReservation, NotReserved
from reservation.domain.value_objects import HOLD_PERIOD_DAYS


def _queue() -> ReservationQueue:
    return ReservationQueue(title_id=uuid.uuid4())


class AddReservationTests(TestCase):
    def test_adds_member_to_the_queue(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()

        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))

        self.assertEqual(len(queue.reservations), 1)
        self.assertEqual(queue.reservations[0].member_id, member_id)

    def test_rejects_duplicate_reservation_from_same_member(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))

        with self.assertRaises(DuplicateReservation):
            queue.add_reservation(member_id=member_id, today=date(2026, 1, 2))

    def test_rejects_reservation_from_member_who_already_holds(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))
        queue.assign_hold(copy_id=uuid.uuid4(), today=date(2026, 1, 2))

        with self.assertRaises(DuplicateReservation):
            queue.add_reservation(member_id=member_id, today=date(2026, 1, 3))

    def test_preserves_fifo_order(self) -> None:
        queue = _queue()
        first, second = uuid.uuid4(), uuid.uuid4()

        queue.add_reservation(member_id=first, today=date(2026, 1, 1))
        queue.add_reservation(member_id=second, today=date(2026, 1, 2))

        self.assertEqual([r.member_id for r in queue.reservations], [first, second])


class CancelReservationTests(TestCase):
    def test_removes_the_members_reservation(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))

        queue.cancel(member_id)

        self.assertEqual(queue.reservations, [])

    def test_raises_when_member_has_no_reservation(self) -> None:
        queue = _queue()

        with self.assertRaises(NotReserved):
            queue.cancel(uuid.uuid4())


class AssignHoldTests(TestCase):
    def test_returns_none_when_no_one_is_waiting(self) -> None:
        queue = _queue()

        result = queue.assign_hold(copy_id=uuid.uuid4(), today=date(2026, 1, 1))

        self.assertIsNone(result)

    def test_converts_front_of_queue_into_a_hold(self) -> None:
        queue = _queue()
        first, second = uuid.uuid4(), uuid.uuid4()
        queue.add_reservation(member_id=first, today=date(2026, 1, 1))
        queue.add_reservation(member_id=second, today=date(2026, 1, 2))
        copy_id = uuid.uuid4()

        hold = queue.assign_hold(copy_id=copy_id, today=date(2026, 1, 10))

        self.assertEqual(hold.member_id, first)
        self.assertEqual(hold.expires_at, date(2026, 1, 10) + timedelta(days=HOLD_PERIOD_DAYS))
        self.assertEqual([r.member_id for r in queue.reservations], [second])
        self.assertEqual(queue.holder_for_copy(copy_id), first)

    def test_records_hold_ready_event(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))

        queue.assign_hold(copy_id=uuid.uuid4(), today=date(2026, 1, 10))
        events = queue.collect_events()

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], HoldReady)
        self.assertEqual(events[0].member_id, member_id)


class ExpireHoldsTests(TestCase):
    def test_removes_expired_hold(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))
        hold = queue.assign_hold(copy_id=uuid.uuid4(), today=date(2026, 1, 1))

        queue.expire_holds(hold.expires_at + timedelta(days=1))

        self.assertEqual(queue.holds, [])

    def test_leaves_unexpired_hold_untouched(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))
        queue.assign_hold(copy_id=uuid.uuid4(), today=date(2026, 1, 1))

        queue.expire_holds(date(2026, 1, 2))

        self.assertEqual(len(queue.holds), 1)

    def test_promotes_next_reservation_to_a_new_hold_for_the_same_copy(self) -> None:
        queue = _queue()
        first, second = uuid.uuid4(), uuid.uuid4()
        queue.add_reservation(member_id=first, today=date(2026, 1, 1))
        queue.add_reservation(member_id=second, today=date(2026, 1, 2))
        copy_id = uuid.uuid4()
        hold = queue.assign_hold(copy_id=copy_id, today=date(2026, 1, 3))
        queue.collect_events()

        queue.expire_holds(hold.expires_at + timedelta(days=1))

        self.assertEqual(queue.holder_for_copy(copy_id), second)
        self.assertEqual(queue.reservations, [])

    def test_records_hold_expired_and_hold_ready_events_on_promotion(self) -> None:
        queue = _queue()
        first, second = uuid.uuid4(), uuid.uuid4()
        queue.add_reservation(member_id=first, today=date(2026, 1, 1))
        queue.add_reservation(member_id=second, today=date(2026, 1, 2))
        copy_id = uuid.uuid4()
        hold = queue.assign_hold(copy_id=copy_id, today=date(2026, 1, 3))
        queue.collect_events()

        queue.expire_holds(hold.expires_at + timedelta(days=1))
        events = queue.collect_events()

        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], HoldExpired)
        self.assertEqual(events[0].member_id, first)
        self.assertIsInstance(events[1], HoldReady)
        self.assertEqual(events[1].member_id, second)

    def test_no_promotion_when_no_one_else_is_waiting(self) -> None:
        queue = _queue()
        member_id = uuid.uuid4()
        queue.add_reservation(member_id=member_id, today=date(2026, 1, 1))
        copy_id = uuid.uuid4()
        hold = queue.assign_hold(copy_id=copy_id, today=date(2026, 1, 1))

        queue.expire_holds(hold.expires_at + timedelta(days=1))

        self.assertEqual(queue.holds, [])
        self.assertIsNone(queue.holder_for_copy(copy_id))
