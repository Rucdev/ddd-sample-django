import uuid

from django.db import models


class TicketModel(models.Model):
    """`Ticket` エンティティの永続化用モデル。注文明細 1 行につき 1 行。

    `order_id` は ordering モジュールの ID を値として持つだけで、ForeignKey は張らない。
    (order_id, line_no) の一意制約は「明細 1 行につきチケット 1 枚」というドメインの前提を
    DB レベルでも保証するため。
    """

    class Status(models.TextChoices):
        # 値はドメインの TicketStatus と揃える(ラベルは画面表示用)。
        QUEUED = "QUEUED", "調理待ち"
        COOKING = "COOKING", "調理中"
        DONE = "DONE", "調理済"
        CANCELLED = "CANCELLED", "取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(db_index=True)
    line_no = models.PositiveSmallIntegerField()  # 注文の中での明細の番号(1 始まり)
    name = models.CharField(max_length=128)
    quantity = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    # 調理済になった時刻。画面の「調理済」列を完了の新しい順に並べるためだけに持つ
    # (ドメインのルールには使わないので、エンティティには載せずリポジトリが記録する)。
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "kitchen_ticket"
        constraints = [
            models.UniqueConstraint(fields=["order_id", "line_no"], name="kitchen_ticket_one_per_line"),
        ]

    def __str__(self) -> str:
        return str(self.id)
