import uuid
from dataclasses import dataclass

from ordering.domain.entities import Order


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


@dataclass(frozen=True)
class OrderDTO:
    """ユースケースの出力・画面表示用の DTO。エンティティや ORM モデルをそのまま
    presentation 層に渡さないための境界。金額は円の整数にほどいて渡す。
    """

    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    lines: tuple[OrderLineDTO, ...]
    subtotal: int
    discount: int
    total: int

    @classmethod
    def from_entity(cls, order: Order) -> "OrderDTO":
        return cls(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status.value,
            lines=tuple(
                OrderLineDTO(
                    menu_item_id=line.menu_item_id,
                    name=line.name,
                    unit_price=line.unit_price.amount,
                    quantity=line.quantity,
                    subtotal=line.subtotal.amount,
                )
                for line in order.lines
            ),
            subtotal=order.subtotal.amount,
            discount=order.discount.amount,
            total=order.total.amount,
        )
