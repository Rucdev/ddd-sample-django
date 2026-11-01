import copy
import uuid

from ordering.domain.entities import Bill, Order
from ordering.domain.value_objects import IN_PROGRESS_STATUSES, BillStatus


class FakeOrderRepository:
    """インメモリの `OrderRepository`。ユースケースのテストで DB の代わりに使う。

    保存・取得のたびにコピーを渡す。本物のリポジトリと同じく「取得したエンティティを
    書き換えても、save するまでは保存済みの状態は変わらない」ようにするため。
    """

    def __init__(self) -> None:
        self._orders: dict[uuid.UUID, Order] = {}
        self.locked: list[uuid.UUID] = []  # for_update=True で読まれた注文(ロックを取ったかの確認用)

    def save(self, order: Order) -> None:
        self._orders[order.id] = copy.deepcopy(order)

    def find_by_id(self, order_id: uuid.UUID, *, for_update: bool = False) -> Order | None:
        if for_update:
            self.locked.append(order_id)
        order = self._orders.get(order_id)
        return copy.deepcopy(order) if order else None

    def count_in_progress_by_customer(self, customer_id: uuid.UUID) -> int:
        return sum(
            1
            for order in self._orders.values()
            if order.customer_id == customer_id and order.status in IN_PROGRESS_STATUSES
        )

    def find_by_bill(self, bill_id: uuid.UUID) -> list[Order]:
        return [copy.deepcopy(order) for order in self._orders.values() if order.bill_id == bill_id]


class FakeBillRepository:
    """インメモリの `BillRepository`。"""

    def __init__(self) -> None:
        self._bills: dict[uuid.UUID, Bill] = {}

    def save(self, bill: Bill) -> None:
        self._bills[bill.id] = copy.deepcopy(bill)

    def find_by_id(self, bill_id: uuid.UUID, *, for_update: bool = False) -> Bill | None:
        bill = self._bills.get(bill_id)
        return copy.deepcopy(bill) if bill else None

    def find_open_by_seat(self, seat_id: uuid.UUID, *, for_update: bool = False) -> Bill | None:
        bill = next(
            (b for b in self._bills.values() if b.seat_id == seat_id and b.status == BillStatus.OPEN),
            None,
        )
        return copy.deepcopy(bill) if bill else None

    def all(self) -> list[Bill]:
        return [copy.deepcopy(bill) for bill in self._bills.values()]
