from django.db import transaction

from ordering.application.dto import OrderDTO, ServeOrderInput
from ordering.domain.exceptions import OrderNotFound
from ordering.domain.repositories import OrderRepository
from shared.infrastructure.event_bus import publish


class ServeOrderUseCase:
    """提供完了ユースケース。店員が店内の注文(提供待ち)を席まで運んだときに呼ぶ。
    支払いは会計でまとめて行うので、ここでは注文のステータスを進めるだけ。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, data: ServeOrderInput) -> OrderDTO:
        with transaction.atomic():
            order = self._order_repository.find_by_id(data.order_id, for_update=True)
            if order is None:
                raise OrderNotFound(data.order_id)

            order.serve()
            self._order_repository.save(order)
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
