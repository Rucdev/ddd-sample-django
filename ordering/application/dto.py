import uuid
from dataclasses import dataclass

from ordering.domain.entities import Bill, Order


# 各ユースケースの入力 DTO。presentation 層(Form / Serializer)が形式チェック済みの値を
# ここに詰め替えてユースケースへ渡す。


@dataclass(frozen=True)
class PlaceOrderLineInput:
    menu_item_id: uuid.UUID
    quantity: int


@dataclass(frozen=True)
class PlaceOrderInput:
    customer_id: uuid.UUID
    lines: tuple[PlaceOrderLineInput, ...]


@dataclass(frozen=True)
class PlaceSeatOrderInput:
    """席からの注文。会員 ID は要らず、どの席からの注文かだけを持つ。"""

    seat_id: uuid.UUID
    lines: tuple[PlaceOrderLineInput, ...]


@dataclass(frozen=True)
class CancelSeatOrderInput:
    seat_id: uuid.UUID
    order_id: uuid.UUID


@dataclass(frozen=True)
class ServeOrderInput:
    order_id: uuid.UUID


@dataclass(frozen=True)
class CancelOrderInput:
    order_id: uuid.UUID


@dataclass(frozen=True)
class PickUpOrderInput:
    order_id: uuid.UUID


@dataclass(frozen=True)
class OrderLineDTO:
    menu_item_id: uuid.UUID
    name: str
    unit_price: int
    quantity: int
    subtotal: int
    cooking_status: str  # WAITING / COOKING / DONE


@dataclass(frozen=True)
class OrderDTO:
    """ユースケースの出力・画面表示用の DTO。エンティティや ORM モデルをそのまま
    presentation 層に渡さないための境界。金額は円の整数にほどいて渡す。
    """

    id: uuid.UUID
    order_type: str  # TAKEOUT / DINE_IN
    customer_id: uuid.UUID | None  # 持ち帰りのみ
    bill_id: uuid.UUID | None  # 店内のみ
    status: str
    lines: tuple[OrderLineDTO, ...]
    subtotal: int
    discount: int
    total: int
    cooked_line_count: int  # できあがった明細の数

    @classmethod
    def from_entity(cls, order: Order) -> "OrderDTO":
        return cls(
            id=order.id,
            order_type=order.order_type.value,
            customer_id=order.customer_id,
            bill_id=order.bill_id,
            status=order.status.value,
            lines=tuple(
                OrderLineDTO(
                    menu_item_id=line.menu_item_id,
                    name=line.name,
                    unit_price=line.unit_price.amount,
                    quantity=line.quantity,
                    subtotal=line.subtotal.amount,
                    cooking_status=line.cooking_status.value,
                )
                for line in order.lines
            ),
            subtotal=order.subtotal.amount,
            discount=order.discount.amount,
            total=order.total.amount,
            cooked_line_count=order.cooked_line_count,
        )


@dataclass(frozen=True)
class BillDTO:
    """席の会計。紐づく注文(明細)と、支払う金額を持つ。"""

    id: uuid.UUID
    seat_id: uuid.UUID
    seat_code: str
    status: str  # OPEN / PAID
    orders: tuple[OrderDTO, ...]
    amount_due: int  # キャンセルした注文を除いた合計

    @classmethod
    def from_entity(cls, bill: Bill, orders: list[Order]) -> "BillDTO":
        return cls(
            id=bill.id,
            seat_id=bill.seat_id,
            seat_code=bill.seat_code,
            status=bill.status.value,
            orders=tuple(OrderDTO.from_entity(order) for order in orders),
            amount_due=bill.amount_due(orders).amount,
        )
