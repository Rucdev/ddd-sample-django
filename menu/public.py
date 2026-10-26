"""Public API of the menu module. Other modules must only import from here."""

import uuid
from dataclasses import dataclass

from menu.models import MenuItem


@dataclass(frozen=True)
class MenuItemDTO:
    id: uuid.UUID
    category_name: str
    name: str
    price: int  # 税込価格(円)
    is_available: bool


def _to_dto(item: MenuItem) -> MenuItemDTO:
    return MenuItemDTO(
        id=item.id,
        category_name=item.category.name,
        name=item.name,
        price=item.price,
        is_available=item.status == MenuItem.Status.ON_SALE and not item.out_of_stock,
    )


def get_menu_item(menu_item_id: uuid.UUID) -> MenuItemDTO | None:
    item = MenuItem.objects.select_related("category").filter(id=menu_item_id).first()
    return _to_dto(item) if item else None


def list_available_menu_items() -> list[MenuItemDTO]:
    """注文画面に並べる「販売中」かつ「在庫切れでない」商品の一覧。"""
    queryset = MenuItem.objects.select_related("category").filter(
        status=MenuItem.Status.ON_SALE, out_of_stock=False
    )
    return [_to_dto(item) for item in queryset]


def set_out_of_stock(menu_item_id: uuid.UUID, out_of_stock: bool) -> None:
    """在庫切れフラグを切り替える。inventory モジュールがキットの注文可能数に合わせて呼ぶ。"""
    MenuItem.objects.filter(id=menu_item_id).update(out_of_stock=out_of_stock)
