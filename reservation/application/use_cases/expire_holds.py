import uuid
from datetime import date

from django.db import transaction

from reservation.domain.repositories import ReservationQueueRepository
from shared.infrastructure.event_bus import publish


class ExpireHoldsUseCase:
    """1 つの書誌の取置期限切れを処理するユースケース。`expire_holds` management
    コマンドが、期限切れの取置を持つ書誌ごとにこれを呼び出す。
    """

    def __init__(self, repository: ReservationQueueRepository) -> None:
        self._repository = repository

    def execute(self, title_id: uuid.UUID, *, today: date | None = None) -> None:
        today = today or date.today()
        with transaction.atomic():
            queue = self._repository.find_by_title(title_id)
            queue.expire_holds(today)
            self._repository.save(queue)
            publish(queue.collect_events())
