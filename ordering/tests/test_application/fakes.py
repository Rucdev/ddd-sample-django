import copy
import uuid

from ordering.domain.entities import Order
from ordering.domain.value_objects import IN_PROGRESS_STATUSES


class FakeOrderRepository:
    """インメモリの `OrderRepository`。ユースケースのテストで DB の代わりに使う。

    保存・取得のたびにコピーを渡す。本物のリポジトリと同じく「取得したエンティティを
    書き換えても、save するまでは保存済みの状態は変わらない」ようにするため。
    """

    def __init__(self) -> None:
        self._orders: dict[uuid.UUID, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.id] = copy.deepcopy(order)

    def find_by_id(self, order_id: uuid.UUID) -> Order | None:
        order = self._orders.get(order_id)
        return copy.deepcopy(order) if order else None

    def count_in_progress_by_customer(self, customer_id: uuid.UUID) -> int:
        return sum(
            1
            for order in self._orders.values()
            if order.customer_id == customer_id and order.status in IN_PROGRESS_STATUSES
        )
