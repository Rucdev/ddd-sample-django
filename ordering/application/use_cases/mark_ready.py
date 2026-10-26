import uuid

from django.db import transaction

from ordering.domain.exceptions import OrderNotFound
from ordering.domain.repositories import OrderRepository
from shared.infrastructure.event_bus import publish


class MarkReadyUseCase:
    """注文を「受取可」にする。kitchen の `CookingCompleted` イベント
    (`ordering/infrastructure/event_handlers.py`)から呼ばれる。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, order_id: uuid.UUID) -> None:
        with transaction.atomic():
            order = self._order_repository.find_by_id(order_id)
            if order is None:
                raise OrderNotFound(order_id)

            order.mark_ready()
            self._order_repository.save(order)
            publish(order.collect_events())
