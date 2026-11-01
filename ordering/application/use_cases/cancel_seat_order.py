from django.db import transaction

from ordering.application.dto import CancelSeatOrderInput, OrderDTO
from ordering.domain.exceptions import OrderNotFound, SeatNotInUse
from ordering.domain.repositories import BillRepository, OrderRepository
from shared.infrastructure.event_bus import publish


class CancelSeatOrderUseCase:
    """席から、その席の注文をキャンセルする。

    キャンセルできる条件(調理開始前)は持ち帰りと同じく Order が判定する。加えて、
    - その席でいま開いている会計の注文であること(別の席・前のお客様の注文は取り消せない)
    - 会計が締まっていないこと(支払済の会計の金額を後から変えない)
    をここで確かめる。
    """

    def __init__(self, order_repository: OrderRepository, bill_repository: BillRepository) -> None:
        self._order_repository = order_repository
        self._bill_repository = bill_repository

    def execute(self, data: CancelSeatOrderInput) -> OrderDTO:
        with transaction.atomic():
            bill = self._bill_repository.find_open_by_seat(data.seat_id, for_update=True)
            if bill is None:
                raise SeatNotInUse(data.seat_id)
            order = self._order_repository.find_by_id(data.order_id, for_update=True)
            if order is None or order.bill_id != bill.id:
                raise OrderNotFound(data.order_id)

            order.cancel()
            self._order_repository.save(order)
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
