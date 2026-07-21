import uuid
from datetime import date

from django.test import TestCase

from reservation.application.use_cases.assign_hold import AssignHoldUseCase
from reservation.domain.entities import ReservationQueue
from reservation.domain.events import HoldReady
from reservation.tests.test_application.fakes import FakeReservationQueueRepository
from shared.infrastructure import event_bus


class AssignHoldUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.title_id = uuid.uuid4()
        self.member_id = uuid.uuid4()
        self.repository = FakeReservationQueueRepository()
        self.use_case = AssignHoldUseCase(repository=self.repository)

        queue = ReservationQueue(title_id=self.title_id)
        queue.add_reservation(member_id=self.member_id, today=date(2026, 1, 1))
        self.repository.save(queue)

    def test_creates_hold_for_front_of_queue(self) -> None:
        copy_id = uuid.uuid4()

        self.use_case.execute(title_id=self.title_id, copy_id=copy_id, today=date(2026, 1, 10))

        queue = self.repository.find_by_title(self.title_id)
        self.assertEqual(queue.holder_for_copy(copy_id), self.member_id)

    def test_publishes_hold_ready_event(self) -> None:
        received = []
        event_bus.subscribe(HoldReady, received.append)
        self.addCleanup(event_bus.unsubscribe, HoldReady, received.append)

        self.use_case.execute(
            title_id=self.title_id, copy_id=uuid.uuid4(), today=date(2026, 1, 10)
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].member_id, self.member_id)

    def test_is_a_no_op_when_no_one_is_waiting(self) -> None:
        empty_title_id = uuid.uuid4()

        self.use_case.execute(
            title_id=empty_title_id, copy_id=uuid.uuid4(), today=date(2026, 1, 10)
        )

        queue = self.repository.find_by_title(empty_title_id)
        self.assertEqual(queue.holds, [])
