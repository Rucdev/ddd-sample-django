import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True)
class OrderedItem:
    """`OrderPlaced` に載せる明細。kitchen が調理チケットを作るのに必要な情報だけを運ぶ。

    kitchen に menu モジュールを照会させないよう、商品名はイベント側に含めておく。
    """

    name: str
    quantity: int


@dataclass(frozen=True, kw_only=True)
class OrderPlaced(DomainEvent):
    """注文が受け付けられたことを表すドメインイベント。kitchen モジュールが購読し、
    調理チケットを作る(kitchen/infrastructure/event_handlers.py)。
    """

    order_id: uuid.UUID
    customer_id: uuid.UUID
    items: tuple[OrderedItem, ...]


@dataclass(frozen=True, kw_only=True)
class OrderCancelled(DomainEvent):
    """注文がキャンセルされたことを表すドメインイベント。kitchen モジュールが購読し、
    調理チケットを取り消す。
    """

    order_id: uuid.UUID
    customer_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class OrderPickedUp(DomainEvent):
    """商品が受け取られたことを表すドメインイベント。customers モジュールが購読し、
    支払額に応じてポイントを付与する(customers/event_handlers.py)。
    """

    order_id: uuid.UUID
    customer_id: uuid.UUID
    total: int  # 割引後の支払額(円)
