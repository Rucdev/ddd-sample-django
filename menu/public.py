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
    image_url: str | None  # 商品画像の URL。未設定なら None


def _to_dto(item: MenuItem) -> MenuItemDTO:
    return MenuItemDTO(
        id=item.id,
        category_name=item.category.name,
        name=item.name,
        price=item.price,
        is_available=item.status == MenuItem.Status.ON_SALE,
        image_url=item.image.url if item.image else None,
    )


def get_menu_item(menu_item_id: uuid.UUID) -> MenuItemDTO | None:
    item = MenuItem.objects.select_related("category").filter(id=menu_item_id).first()
    return _to_dto(item) if item else None


def list_available_menu_items() -> list[MenuItemDTO]:
    """注文画面に並べる「販売中」の商品の一覧。"""
    queryset = MenuItem.objects.select_related("category").filter(
        status=MenuItem.Status.ON_SALE
    )
    return [_to_dto(item) for item in queryset]

