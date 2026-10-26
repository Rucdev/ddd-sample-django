"""参照系(CQRS の Q)。リポジトリを経由せず ORM を直読みして DTO に詰め替える。

一覧表示のためだけにエンティティを組み立てるのは過剰なので、参照系は素直に ORM から
DTO へ変換してよい、というのが directory-structure.md の方針。

ただし金額(小計・割引・合計)の計算ルールはドメイン層にしかないので、ここで計算式を
書き直すことはせず、ORM モデルをエンティティに変換してから DTO にする。
"""

import uuid

from ordering.application.dto import OrderDTO
from ordering.infrastructure.models import OrderModel
from ordering.infrastructure.repositories import order_from_model


def _to_dto(model: OrderModel) -> OrderDTO:
    return OrderDTO.from_entity(order_from_model(model))


def list_orders() -> list[OrderDTO]:
    queryset = OrderModel.objects.prefetch_related("lines").order_by("-created_at")
    return [_to_dto(model) for model in queryset]


def list_orders_for_customer(customer_id: uuid.UUID) -> list[OrderDTO]:
    queryset = (
        OrderModel.objects.prefetch_related("lines")
        .filter(customer_id=customer_id)
        .order_by("-created_at")
    )
    return [_to_dto(model) for model in queryset]


def get_order(order_id: uuid.UUID) -> OrderDTO | None:
    model = OrderModel.objects.prefetch_related("lines").filter(id=order_id).first()
    return _to_dto(model) if model else None
