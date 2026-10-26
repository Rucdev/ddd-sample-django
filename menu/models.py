import uuid

from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class MenuItem(models.Model):
    class Status(models.TextChoices):
        ON_SALE = "ON_SALE", "販売中"
        SOLD_OUT = "SOLD_OUT", "品切れ"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=128, unique=True)
    price = models.PositiveIntegerField(help_text="税込価格(円)")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ON_SALE)
    # 在庫切れは inventory モジュールだけが書き換える(menu.public.set_out_of_stock)。
    # スタッフが手で付ける「品切れ」(status)とは別に持ち、互いに上書きしないようにする。
    out_of_stock = models.BooleanField(
        default=False, help_text="キットの注文可能数が 0 のとき在庫管理が自動で立てる"
    )

    class Meta:
        ordering = ["category__display_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.price}円)"
