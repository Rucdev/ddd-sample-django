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
    # 注文画面のカードに出す商品画像。ImageField(Pillow 依存)ではなく拡張子だけを検査する
    # FileField にしている。未設定なら画面側で代わりの絵を出す。
    # SVG はスクリプトを埋め込めるので、アップロードは受け付けない(画像の URL を直接開かれると
    # このサイトのオリジンでスクリプトが動く = 保存型 XSS)。デモデータの SVG
    # (media/menu_items/demo/)はリポジトリで管理している信頼できるファイルで、fixture から
    # パスを直接入れているので、このバリデータは通らない。
    image = models.FileField(
        upload_to="menu_items/",
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "webp"])],
        help_text="注文画面に表示する商品画像(png / jpg / webp)",
    )

    class Meta:
        ordering = ["category__display_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.price}円)"
