import uuid

from django.db import models


class ReservationModel(models.Model):
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title_id = models.UUIDField(db_index=True)
    copy_id = models.UUIDField(unique=True)
    member_id = models.UUIDField(db_index=True)
    expires_at = models.DateField()

    class Meta:
        db_table = "reservation_hold"

    def __str__(self) -> str:
        return str(self.id)
