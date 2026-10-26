import uuid

from ordering.domain.entities import Order
from ordering.domain.value_objects import (
    IN_PROGRESS_STATUSES,
    DiscountRate,
    Money,
    OrderLine,
    OrderStatus,
)
from ordering.infrastructure.models import OrderLineModel, OrderModel


class DjangoOrderRepository:
    """`OrderRepository` の Django ORM 実装。`Order` エンティティ ⇔ `OrderModel` /
    `OrderLineModel` の変換をここに閉じ込める。

    明細は保存のたびに一度 delete してから bulk_create で作り直す(差分更新はしない)。
    明細は注文後に変わらないので実際には初回保存のときしか中身は変わらないが、
    「集約を丸ごと保存する」形にそろえておくほうが読みやすい。
    """

    def save(self, order: Order) -> None:
        model, _ = OrderModel.objects.update_or_create(
            id=order.id,
            defaults={
                "customer_id": order.customer_id,
                "status": order.status.value,
                "discount_percent": order.discount_rate.percent,
            },
        )
        model.lines.all().delete()
        OrderLineModel.objects.bulk_create(
            OrderLineModel(
                order=model,
                menu_item_id=line.menu_item_id,
                name=line.name,
                unit_price=line.unit_price.amount,
                quantity=line.quantity,
            )
            for line in order.lines
        )

    def find_by_id(self, order_id: uuid.UUID) -> Order | None:
        model = OrderModel.objects.prefetch_related("lines").filter(id=order_id).first()
        return order_from_model(model) if model else None

    def count_in_progress_by_customer(self, customer_id: uuid.UUID) -> int:
        return OrderModel.objects.filter(
            customer_id=customer_id, status__in=[s.value for s in IN_PROGRESS_STATUSES]
        ).count()


def order_from_model(model: OrderModel) -> Order:
    """ORM モデル → `Order` エンティティ。参照系(application/queries.py)でも金額計算を
    ドメイン側に任せるために使う。明細は `prefetch_related("lines")` 済みであること。
    """
    return Order(
        order_id=model.id,
        customer_id=model.customer_id,
        lines=[
            OrderLine(
                menu_item_id=line.menu_item_id,
                name=line.name,
                unit_price=Money(line.unit_price),
                quantity=line.quantity,
            )
            for line in model.lines.all()
        ],
        discount_rate=DiscountRate(model.discount_percent),
        status=OrderStatus(model.status),
    )
