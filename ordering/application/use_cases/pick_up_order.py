from django.db import transaction

from ordering.application.dto import OrderDTO, PickUpOrderInput
from ordering.domain.exceptions import OrderNotFound
from ordering.domain.repositories import OrderRepository
from shared.infrastructure.event_bus import publish


class PickUpOrderUseCase:
    """受取ユースケース。`OrderPickedUp` イベントの発行が、customers モジュールの
    ポイント付与のきっかけになる。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, data: PickUpOrderInput) -> OrderDTO:
        with transaction.atomic():
            order = self._order_repository.find_by_id(data.order_id)
            if order is None:
                raise OrderNotFound(data.order_id)

            order.pick_up()
            self._order_repository.save(order)
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
