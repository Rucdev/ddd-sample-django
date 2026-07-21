import uuid
from datetime import date

from django.db import transaction

from reservation.domain.repositories import ReservationQueueRepository
from shared.infrastructure.event_bus import publish


class AssignHoldUseCase:
    """返却されたばかりの蔵書を、待ち行列の先頭の予約者のために取置に変える。

    lending の `BookReturned` イベント(`reservation/infrastructure/event_handlers.py`)
    から呼ばれる。誰も待っていなければ何もしない(冪等)。
    """

    def __init__(self, repository: ReservationQueueRepository) -> None:
        self._repository = repository

    def execute(self, *, title_id: uuid.UUID, copy_id: uuid.UUID, today: date) -> None:
        with transaction.atomic():
            queue = self._repository.find_by_title(title_id)
            queue.assign_hold(copy_id=copy_id, today=today)
            self._repository.save(queue)
            publish(queue.collect_events())
