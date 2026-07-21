import uuid
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from reservation.domain.entities import ReservationQueue
from reservation.infrastructure.repositories import DjangoReservationQueueRepository


class ExpireHoldsCommandTests(TestCase):
    def setUp(self) -> None:
        self.repository = DjangoReservationQueueRepository()

    def test_expires_hold_and_promotes_next_reservation(self) -> None:
        title_id = uuid.uuid4()
        first, second = uuid.uuid4(), uuid.uuid4()
        copy_id = uuid.uuid4()

        queue = ReservationQueue(title_id=title_id)
        queue.add_reservation(member_id=first, today=date.today() - timedelta(days=20))
        queue.add_reservation(member_id=second, today=date.today() - timedelta(days=19))
        queue.assign_hold(copy_id=copy_id, today=date.today() - timedelta(days=10))
        queue.collect_events()
        self.repository.save(queue)

        call_command("expire_holds")

        updated = self.repository.find_by_title(title_id)
        self.assertEqual(updated.holder_for_copy(copy_id), second)

    def test_leaves_unexpired_holds_untouched(self) -> None:
        title_id = uuid.uuid4()
        member_id = uuid.uuid4()
        copy_id = uuid.uuid4()

        queue = ReservationQueue(title_id=title_id)
        queue.add_reservation(member_id=member_id, today=date.today())
        queue.assign_hold(copy_id=copy_id, today=date.today())
        queue.collect_events()
        self.repository.save(queue)

        call_command("expire_holds")

        updated = self.repository.find_by_title(title_id)
        self.assertEqual(updated.holder_for_copy(copy_id), member_id)
