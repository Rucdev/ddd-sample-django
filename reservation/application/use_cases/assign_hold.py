import uuid
from datetime import date

from django.db import transaction

from reservation.domain.repositories import ReservationQueueRepository
from shared.infrastructure.event_bus import publish


class AssignHoldUseCase:
    """Converts the front of a title's reservation queue into a hold on a just-returned copy.

    Triggered by lending's BookReturned event; a no-op if nobody is waiting.
    """

    def __init__(self, repository: ReservationQueueRepository) -> None:
        self._repository = repository

    def execute(self, *, title_id: uuid.UUID, copy_id: uuid.UUID, today: date) -> None:
        with transaction.atomic():
            queue = self._repository.find_by_title(title_id)
            queue.assign_hold(copy_id=copy_id, today=today)
            self._repository.save(queue)
            publish(queue.collect_events())
