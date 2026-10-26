import uuid

from ordering.domain.exceptions import TooManyInProgressOrders
from ordering.domain.repositories import OrderRepository

# 1 人のお客様が同時に進行中(受取前)にできる注文数の上限。
MAX_IN_PROGRESS_ORDERS = 3


class OrderPolicy:
    """ドメインサービス。1 つのエンティティに閉じない判定(お客様の注文をまたいだ件数の集計)
    を担う。リポジトリの集計メソッドを使うので、Order エンティティ自身には持たせない。
    """

    def __init__(
        self, order_repository: OrderRepository, limit: int = MAX_IN_PROGRESS_ORDERS
    ) -> None:
        self._order_repository = order_repository
        self._limit = limit

    def ensure_customer_can_order(self, customer_id: uuid.UUID) -> None:
        if self._order_repository.count_in_progress_by_customer(customer_id) >= self._limit:
            raise TooManyInProgressOrders(customer_id, self._limit)
