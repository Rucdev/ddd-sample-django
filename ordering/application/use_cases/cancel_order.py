from django.db import transaction

from ordering.application.dto import CancelOrderInput, OrderDTO
from ordering.domain.exceptions import OrderNotFound
from ordering.domain.repositories import OrderRepository
from shared.infrastructure.event_bus import publish


class CancelOrderUseCase:
    """キャンセルユースケース。`OrderCancelled` イベントの発行が、kitchen モジュールの
    調理チケット取消のきっかけになる。調理開始後かどうかの判定は Order 自身が持つ
    ステータスだけで行える(kitchen への照会は要らない)。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, data: CancelOrderInput) -> OrderDTO:
        with transaction.atomic():
            order = self._order_repository.find_by_id(data.order_id)
            if order is None:
                raise OrderNotFound(data.order_id)

            order.cancel()
            self._order_repository.save(order)
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
