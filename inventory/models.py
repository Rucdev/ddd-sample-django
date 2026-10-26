import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Kit(models.Model):
    """商品 1 個を作るためのキット。商品(menu の MenuItem)とは 1 対 1。

    `menu_item_id` は menu モジュールの ID を値として持つだけで、ForeignKey は張らない。
    実在庫数・予約数は inventory/services.py の関数だけが書き換える(admin / API では読み取り専用)。
    予約数は確保中の予約(Reservation)の数量の合計で、条件付き UPDATE 1 本で
    「注文可能数が足りるか」を判定できるように、ここにも持っておく。
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "管理中"
        INACTIVE = "INACTIVE", "管理停止"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item_id = models.UUIDField(unique=True)
    name = models.CharField(max_length=128)
    on_hand = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            # 実在庫 ≥ 確保中の予約数。services.py の条件付き UPDATE で守っているが、DB でも保証する。
            models.CheckConstraint(
                condition=Q(on_hand__gte=F("reserved")), name="kit_on_hand_covers_reserved"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def available(self) -> int:
        """注文可能数 = 実在庫 − 確保中の予約数。"""
        return self.on_hand - self.reserved

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class Reservation(models.Model):
    """スタッフが手で押さえておくキット(団体注文・イベント用など)。

    確保中の間は注文に使えない。「使用」で確保した数をすべて実在庫から引き、「取消」で解放する。
    """

    class Status(models.TextChoices):
        HELD = "HELD", "確保中"
        USED = "USED", "使用済"
        CANCELLED = "CANCELLED", "取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(Kit, on_delete=models.PROTECT, related_name="reservations")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    memo = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.HELD)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.kit.name} x {self.quantity} ({self.get_status_display()})"


class StockMovement(models.Model):
    """実在庫が動いた記録(在庫ログ)。実在庫の変化 = ログの増減量の合計、が常に成り立つ。

    予約の確保・取消は実在庫を動かさないので記録しない(予約そのものが履歴になる)。
    `order_id` は ordering モジュールの ID を値として持つだけ。
    """

    class Kind(models.TextChoices):
        RECEIPT = "RECEIPT", "入庫"
        ISSUE = "ISSUE", "出庫"
        ORDER_ALLOCATION = "ORDER_ALLOCATION", "注文で消費"
        ORDER_RELEASE = "ORDER_RELEASE", "キャンセルで戻し"
        RESERVATION_USE = "RESERVATION_USE", "予約を使用"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(Kit, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    change = models.IntegerField(help_text="実在庫の増減量(入庫は正、出庫・消費は負)")
    on_hand_after = models.PositiveIntegerField(help_text="この変動を反映した後の実在庫")
    memo = models.CharField(max_length=255, blank=True)
    order_id = models.UUIDField(null=True, blank=True, db_index=True)
    reservation = models.ForeignKey(
        Reservation, on_delete=models.PROTECT, null=True, blank=True, related_name="movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kit.name} {self.change:+d} ({self.get_kind_display()})"
