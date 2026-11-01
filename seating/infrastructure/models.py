import uuid

from django.db import models


class AreaModel(models.Model):
    """エリアの永続化用モデル。座席構成ファイルの写しで、`apply_seat_layout` だけが書き換える。"""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "seating_area"
        ordering = ["display_order"]

    def __str__(self) -> str:
        return self.name


class SeatModel(models.Model):
    """`Seat` エンティティの永続化用モデル。

    エリア・定員・位置は座席構成ファイルから `apply_seat_layout` が書き、ステータスは画面・API
    → ユースケース経由でだけ書き換わる。位置の重なりはドメイン(SeatLayout)で検査しているので
    DB 制約にはしていない(席同士が位置を入れ替える構成変更を 1 席ずつ保存できるように)。
    """

    class Status(models.TextChoices):
        # 値はドメインの SeatStatus と揃える(ラベルは画面表示用)。
        AVAILABLE = "AVAILABLE", "空き"
        RESERVED = "RESERVED", "予約中"
        OCCUPIED = "OCCUPIED", "使用中"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    # 同じモジュールの中なので ForeignKey を張る(モジュールをまたぐ FK は張らない、のルールの対象外)。
    area = models.ForeignKey(AreaModel, on_delete=models.PROTECT, related_name="seats")
    capacity = models.PositiveIntegerField()
    row = models.PositiveIntegerField()
    col = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE)
    # 画面で「使用中 25 分」のように出すための記録。ドメインのルールには使わないので
    # エンティティには持たせず、リポジトリがステータスの変化を見て更新する。
    status_changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seating_seat"
        ordering = ["area__display_order", "row", "col"]

    def __str__(self) -> str:
        return self.code
