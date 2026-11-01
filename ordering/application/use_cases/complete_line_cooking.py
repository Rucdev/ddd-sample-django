import uuid

from django.db import transaction

from ordering.domain.exceptions import OrderNotFound
from ordering.domain.repositories import OrderRepository
from shared.infrastructure.event_bus import publish


class CompleteLineCookingUseCase:
    """明細 1 行の調理完了を注文に記録する(全部の明細がそろうと注文は「受取可」になる)。
    kitchen の `CookingCompleted` イベント(`ordering/infrastructure/event_handlers.py`)から呼ばれる。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, order_id: uuid.UUID, line_no: int) -> None:
        with transaction.atomic():
            order = self._order_repository.find_by_id(order_id, for_update=True)
            if order is None:
                raise OrderNotFound(order_id)

            order.complete_cooking_line(line_no)
            self._order_repository.save(order)
            publish(order.collect_events())
