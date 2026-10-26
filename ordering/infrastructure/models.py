import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class OrderModel(models.Model):
    """`Order` エンティティの永続化用モデル(ORM モデル)。ドメイン層のエンティティとは
    あえて別クラスにしており、`DjangoOrderRepository` が相互変換を担う。

    `customer_id` は customers モジュールの ID を値として保持するだけで、ForeignKey は
    張らない(モジュールをまたぐ DB レベルの結合を避けるため)。
    """

    class Status(models.TextChoices):
        # 値はドメインの OrderStatus と揃える(ラベルは画面表示用)。
        PLACED = "PLACED", "受付済"
        PREPARING = "PREPARING", "調理中"
        READY = "READY", "受取可"
        PICKED_UP = "PICKED_UP", "受取済"
        CANCELLED = "CANCELLED", "キャンセル"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.UUIDField(db_index=True)
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

    class Meta:
        db_table = "ordering_order_line"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} x {self.quantity}"
