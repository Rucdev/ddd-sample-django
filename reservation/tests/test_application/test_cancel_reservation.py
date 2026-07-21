import uuid
from datetime import date

from django.test import TestCase

from reservation.application.dto import CancelReservationInput
from reservation.application.use_cases.cancel_reservation import CancelReservationUseCase
from reservation.domain.entities import ReservationQueue
from reservation.domain.exceptions import NotReserved
from reservation.tests.test_application.fakes import FakeReservationQueueRepository


class CancelReservationUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.title_id = uuid.uuid4()
        self.member_id = uuid.uuid4()
        self.repository = FakeReservationQueueRepository()
        self.use_case = CancelReservationUseCase(repository=self.repository)

        queue = ReservationQueue(title_id=self.title_id)
        queue.add_reservation(member_id=self.member_id, today=date(2026, 1, 1))
        self.repository.save(queue)

    def test_cancels_pending_reservation(self) -> None:
        self.use_case.execute(
            CancelReservationInput(member_id=self.member_id, title_id=self.title_id)
        )

        queue = self.repository.find_by_title(self.title_id)
        self.assertEqual(queue.reservations, [])

    def test_raises_when_member_has_no_reservation(self) -> None:
        with self.assertRaises(NotReserved):
            self.use_case.execute(
                CancelReservationInput(member_id=uuid.uuid4(), title_id=self.title_id)
            )
