import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class OrderModel(models.Model):
    """`Order` エンティティの永続化用モデル(ORM モデル)。ドメイン層のエンティティとは
    あえて別クラスにしており、`DjangoOrderRepository` が相互変換を担う。

    `customer_id` は customers モジュールの ID を値として保持するだけで、ForeignKey は
    張らない(モジュールをまたぐ DB レベルの結合を避けるため)。持ち帰りの注文は
    `customer_id`、店内の注文は `bill`(同じモジュールの会計)を持つ。
    """

    class OrderType(models.TextChoices):
        # 値はドメインの OrderType と揃える。
        TAKEOUT = "TAKEOUT", "持ち帰り"
        DINE_IN = "DINE_IN", "店内"

    class Status(models.TextChoices):
        # 値はドメインの OrderStatus と揃える(ラベルは画面表示用)。
        # READY は持ち帰りなら「受取可」、店内なら「提供待ち」と画面側で呼び分ける。
        PLACED = "PLACED", "受付済"
        PREPARING = "PREPARING", "調理中"
        READY = "READY", "受取可 / 提供待ち"
        PICKED_UP = "PICKED_UP", "受取済"
        SERVED = "SERVED", "提供済"
        CANCELLED = "CANCELLED", "キャンセル"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_type = models.CharField(max_length=16, choices=OrderType.choices, default=OrderType.TAKEOUT)
    customer_id = models.UUIDField(db_index=True, null=True, blank=True)
    # 同じモジュールの中なので ForeignKey を張る。PROTECT: 注文が残っている会計は消させない。
    bill = models.ForeignKey(
        "BillModel", on_delete=models.PROTECT, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    # 一覧の並び順のためだけに持つ。ドメインのルールは時刻に依存しないので
    # エンティティには載せていない。
    created_at = models.DateTimeField(auto_now_add=True)

    # OrderLineModel.order の related_name で生える逆参照。型チェッカー向けの宣言だけで、
    # フィールドは増えない(ty は django-stubs の mypy プラグインを使えず、逆参照を推論できない)。
    lines: "RelatedManager[OrderLineModel]"

    class Meta:
        db_table = "ordering_order"
        constraints = [
            # ドメインの不変条件(持ち帰りは会員、店内は会計のどちらか一方だけを持つ)を DB でも守る。
            models.CheckConstraint(
                condition=(
                    models.Q(order_type="TAKEOUT", customer_id__isnull=False, bill__isnull=True)
                    | models.Q(order_type="DINE_IN", customer_id__isnull=True, bill__isnull=False)
                ),
                name="ordering_order_owner_matches_type",
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)


class OrderLineModel(models.Model):
    """`Order` 集約が持つ明細 1 行分の永続化用モデル。

    `order` は同一モジュール内なので ForeignKey を張ってよい。`menu_item_id` は menu
    モジュールの ID なので値として持つだけ。商品名・単価は注文時点のスナップショット。
    """

    order = models.ForeignKey(OrderModel, on_delete=models.CASCADE, related_name="lines")
    menu_item_id = models.UUIDField()
    name = models.CharField(max_length=128)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveSmallIntegerField()
    # キッチンでの調理状況(ドメインの LineCookingStatus)。明細の並び(id 順)が line_no になる。
    cooking_status = models.CharField(max_length=16, default="WAITING")

    class Meta:
        db_table = "ordering_order_line"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} x {self.quantity}"


class BillModel(models.Model):
    """`Bill` エンティティ(席の会計)の永続化用モデル。

    `seat_id` は seating モジュールの ID を値として持つだけで、ForeignKey は張らない。
    `seat_code` は画面表示用の写し(席コード)。
    """

    class Status(models.TextChoices):
        # 値はドメインの BillStatus と揃える。
        OPEN = "OPEN", "利用中"
        PAID = "PAID", "支払済"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seat_id = models.UUIDField(db_index=True)
    seat_code = models.CharField(max_length=32)
    status = models.CharField(max_length=8, choices=Status.choices)
    # 表示・並び順のためだけに持つ(ドメインのルールは時刻に依存しない)。
    opened_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    orders: "RelatedManager[OrderModel]"

    class Meta:
        db_table = "ordering_bill"
        constraints = [
            # 1 つの席に開いている会計は高々 1 つ。
            models.UniqueConstraint(
                fields=["seat_id"],
                condition=models.Q(status="OPEN"),
                name="ordering_bill_one_open_per_seat",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.seat_code} ({self.get_status_display()})"
