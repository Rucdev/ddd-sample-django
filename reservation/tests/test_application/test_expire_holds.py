import uuid
from datetime import date, timedelta

from django.test import TestCase

from reservation.application.use_cases.expire_holds import ExpireHoldsUseCase
from reservation.domain.entities import ReservationQueue
from reservation.domain.events import HoldExpired
from reservation.tests.test_application.fakes import FakeReservationQueueRepository
from shared.infrastructure import event_bus


class ExpireHoldsUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.title_id = uuid.uuid4()
        self.member_id = uuid.uuid4()
        self.repository = FakeReservationQueueRepository()
        self.use_case = ExpireHoldsUseCase(repository=self.repository)

    def _seed_expiring_hold(self):
        queue = ReservationQueue(title_id=self.title_id)
        queue.add_reservation(member_id=self.member_id, today=date(2026, 1, 1))
        copy_id = uuid.uuid4()
        hold = queue.assign_hold(copy_id=copy_id, today=date(2026, 1, 1))
        queue.collect_events()
        self.repository.save(queue)
        return copy_id, hold

    def test_expires_hold_past_expiry(self) -> None:
        copy_id, hold = self._seed_expiring_hold()

        self.use_case.execute(self.title_id, today=hold.expires_at + timedelta(days=1))

        updated = self.repository.find_by_title(self.title_id)
        self.assertIsNone(updated.holder_for_copy(copy_id))

    def test_publishes_hold_expired_event(self) -> None:
        _, hold = self._seed_expiring_hold()
        received = []
        event_bus.subscribe(HoldExpired, received.append)
        self.addCleanup(event_bus.unsubscribe, HoldExpired, received.append)

        self.use_case.execute(self.title_id, today=hold.expires_at + timedelta(days=1))

        self.assertEqual(len(received), 1)
