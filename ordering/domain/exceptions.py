import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# ordering 独自の例外は shared.domain.exceptions の NotFoundError / ConflictError も
# 多重継承しておく。presentation 層(DRF の exception handler)はこの共通基底だけを見て
# 404 / 409 に変換するので、ordering の例外を個別に知らなくて済む(shared → 各モジュール
# への依存が生まれない)。同時に OrderingError を継いでいるので、ordering の view/API 側は
# 「ordering のドメイン例外はまとめて捕まえる」という書き方もできる。


class OrderingError(DomainError):
    """Base class for ordering domain errors."""


class OrderNotFound(OrderingError, NotFoundError):
    def __init__(self, order_id: uuid.UUID) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} was not found")


class OrderLineNotFound(OrderingError, NotFoundError):
    def __init__(self, order_id: uuid.UUID, line_no: int) -> None:
        self.order_id = order_id
        self.line_no = line_no
        super().__init__(f"Order {order_id} has no line {line_no}")


class CustomerNotEligible(OrderingError, ConflictError):
    def __init__(self, customer_id: uuid.UUID) -> None:
        self.customer_id = customer_id
        super().__init__(f"Customer {customer_id} is not eligible to place orders")


class MenuItemNotAvailable(OrderingError, ConflictError):
    def __init__(self, menu_item_id: uuid.UUID) -> None:
        self.menu_item_id = menu_item_id
        super().__init__(f"Menu item {menu_item_id} is not available")


class EmptyOrder(OrderingError, ConflictError):
    def __init__(self) -> None:
        super().__init__("An order must have at least one line")


class InvalidQuantity(OrderingError, ConflictError):
    def __init__(self, name: str, quantity: int) -> None:
        self.name = name
        self.quantity = quantity
        super().__init__(f"Quantity {quantity} for {name} is out of range")


class TooManyInProgressOrders(OrderingError, ConflictError):
    def __init__(self, customer_id: uuid.UUID, limit: int) -> None:
        self.customer_id = customer_id
        self.limit = limit
        super().__init__(f"Customer {customer_id} already has {limit} orders in progress")


class InvalidOrderTransition(OrderingError, ConflictError):
    """ステータス遷移の規則に反する操作(受取可になる前に受け取る、調理開始後にキャンセルする等)。"""

    def __init__(self, order_id: uuid.UUID, current: str, action: str) -> None:
        self.order_id = order_id
        self.current = current
        self.action = action
        super().__init__(f"Order {order_id} cannot {action} while {current}")


class BillNotFound(OrderingError, NotFoundError):
    def __init__(self, bill_id: uuid.UUID) -> None:
        self.bill_id = bill_id
        super().__init__(f"Bill {bill_id} was not found")


class SeatNotInUse(OrderingError, ConflictError):
    """席からの注文を受けたが、その席の会計が開いていない(席が使用中でない)。"""

    def __init__(self, seat_id: uuid.UUID) -> None:
        self.seat_id = seat_id
        super().__init__(f"Seat {seat_id} is not in use, so it cannot take orders")


class InvalidBillTransition(OrderingError, ConflictError):
    def __init__(self, bill_id: uuid.UUID, current: str, action: str) -> None:
        self.bill_id = bill_id
        self.current = current
        self.action = action
        super().__init__(f"Bill {bill_id} cannot {action} while {current}")
