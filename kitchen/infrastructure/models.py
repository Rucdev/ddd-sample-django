import uuid

from django.db import models


class TicketModel(models.Model):
    """`Ticket` エンティティの永続化用モデル。

    `order_id` は ordering モジュールの ID を値として持つだけで、ForeignKey は張らない。
    一意制約は「注文 1 件につきチケット 1 枚」というドメインの前提を DB レベルでも保証するため。

    明細(TicketItem のリスト)は別テーブルにせず JSONField に入れている。明細で検索・集計
    することがなく、チケットと一緒に読み書きするだけの値オブジェクトの列なので、これで十分
    (ordering の OrderLineModel は別テーブルにしている。比較用に方式を変えてある)。
    """

    class Status(models.TextChoices):
        # 値はドメインの TicketStatus と揃える(ラベルは画面表示用)。
        QUEUED = "QUEUED", "調理待ち"
        COOKING = "COOKING", "調理中"
        DONE = "DONE", "調理済"
        CANCELLED = "CANCELLED", "取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(unique=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    items = models.JSONField()  # [{"name": "カフェラテ", "quantity": 2}, ...]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kitchen_ticket"

    def __str__(self) -> str:
        return str(self.id)
