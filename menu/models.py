import uuid

from django.core.validators import FileExtensionValidator
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
    # 注文画面のカードに出す商品画像。SVG も置けるよう ImageField(Pillow 依存)ではなく
    # 拡張子だけを検査する FileField にしている。未設定なら画面側で代わりの絵を出す。
    image = models.FileField(
        upload_to="menu_items/",
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "webp", "svg"])],
        help_text="注文画面に表示する商品画像(png / jpg / webp / svg)",
    )

    class Meta:
        ordering = ["category__display_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.price}円)"
