"""参照系(CQRS の Q)。リポジトリを経由せず ORM を直読みして DTO に詰め替える。

一覧表示のためだけにエンティティを組み立てるのは過剰なので、参照系は素直に ORM から
DTO へ変換してよい、というのが directory-structure.md の方針。

ただし金額(小計・割引・合計)の計算ルールはドメイン層にしかないので、ここで計算式を
書き直すことはせず、ORM モデルをエンティティに変換してから DTO にする。
"""

import uuid

from django.db.models import Prefetch

from ordering.application.dto import BillDTO, OrderDTO
from ordering.domain.value_objects import BillStatus, OrderType
from ordering.infrastructure.models import BillModel, OrderModel
from ordering.infrastructure.repositories import bill_from_model, order_from_model


def _to_dto(model: OrderModel) -> OrderDTO:
    return OrderDTO.from_entity(order_from_model(model))


def list_orders(order_type: OrderType | None = None) -> list[OrderDTO]:
    """注文の一覧(新しい順)。`order_type` を渡すとその種類の注文だけに絞る。"""
    queryset = OrderModel.objects.prefetch_related("lines").order_by("-created_at")
    if order_type is not None:
        queryset = queryset.filter(order_type=order_type.value)
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


# --- 席の会計 -----------------------------------------------------------------
# 会計の金額(キャンセルを除いた注文の合計)もドメインのルールなので、エンティティに戻してから
# DTO にする(注文と同じ方針)。


def _bills_with_orders():
    return BillModel.objects.prefetch_related(
        Prefetch(
            "orders",
            queryset=OrderModel.objects.prefetch_related("lines").order_by("created_at"),
        )
    )


def _bill_to_dto(model: BillModel) -> BillDTO:
    orders = [order_from_model(order) for order in model.orders.all()]
    return BillDTO.from_entity(bill_from_model(model), orders)


def get_open_bill_for_seat(seat_id: uuid.UUID) -> BillDTO | None:
    """その席でいま開いている会計(席からの注文画面用)。席が使用中でなければ None。"""
    model = _bills_with_orders().filter(seat_id=seat_id, status=BillStatus.OPEN.value).first()
    return _bill_to_dto(model) if model else None


def list_open_bills() -> list[BillDTO]:
    """開いている会計の一覧(ホール画面用)。席コード順。"""
    queryset = _bills_with_orders().filter(status=BillStatus.OPEN.value).order_by("seat_code")
    return [_bill_to_dto(model) for model in queryset]


def list_recently_paid_bills(limit: int = 10) -> list[BillDTO]:
    """支払済になった会計を新しい順に(ホール画面で直近の会計を確かめる用)。"""
    queryset = _bills_with_orders().filter(status=BillStatus.PAID.value).order_by("-paid_at")[:limit]
    return [_bill_to_dto(model) for model in queryset]
