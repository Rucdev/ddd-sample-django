import uuid

from django.db import models


class ReservationModel(models.Model):
    """`ReservationQueue` 集約が持つ「待機中の予約」1 件分の永続化用モデル。
    `title_id` / `member_id` は catalog / members モジュールの ID を値として持つだけで、
    ForeignKey は張らない。

    (title_id, member_id) の一意制約は、ドメイン側の「同一会員の重複予約は不可」という
    ルールを DB レベルでも保証するためのもの。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title_id = models.UUIDField(db_index=True)
    member_id = models.UUIDField(db_index=True)
    requested_at = models.DateField()

    class Meta:
        db_table = "reservation_reservation"
        ordering = ["requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title_id", "member_id"], name="unique_reservation_per_title_member"
            )
        ]

    def __str__(self) -> str:
        return str(self.id)


class HoldModel(models.Model):
    """`ReservationQueue` 集約が持つ「取置」1 件分の永続化用モデル。

    `copy_id` に一意制約を付けているのは、1 つの蔵書(個体)は同時に 1 人にしか
    取置できないというドメインの前提を DB レベルでも保証するため。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title_id = models.UUIDField(db_index=True)
    copy_id = models.UUIDField(unique=True)
    member_id = models.UUIDField(db_index=True)
    expires_at = models.DateField()

    class Meta:
        db_table = "reservation_hold"

    def __str__(self) -> str:
        return str(self.id)
