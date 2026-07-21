from django.db import transaction

from reservation.application.dto import CancelReservationInput
from reservation.domain.repositories import ReservationQueueRepository
from shared.infrastructure.event_bus import publish


class CancelReservationUseCase:
    def __init__(self, repository: ReservationQueueRepository) -> None:
        self._repository = repository

    def execute(self, data: CancelReservationInput) -> None:
        with transaction.atomic():
            queue = self._repository.find_by_title(data.title_id)
            queue.cancel(data.member_id)
            self._repository.save(queue)
            publish(queue.collect_events())
