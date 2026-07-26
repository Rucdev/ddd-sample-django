import uuid

from django.conf import settings
from django.db import models


class Member(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "有効"
        SUSPENDED = "SUSPENDED", "停止"

    class Rank(models.TextChoices):
        REGULAR = "REGULAR", "一般会員"
        SILVER = "SILVER", "シルバー会員"
        GOLD = "GOLD", "ゴールド会員"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    rank = models.CharField(max_length=16, choices=Rank.choices, default=Rank.REGULAR)

    def __str__(self) -> str:
        return self.name
