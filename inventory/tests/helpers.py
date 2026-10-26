"""テスト用のデータ作成ヘルパ。menu の商品はテストに限って ORM モデルを直接使って作る。"""

from inventory import services
from inventory.models import Kit
from menu.models import Category, MenuItem


def create_menu_item(name: str = "ホットサンド", price: int = 600) -> MenuItem:
    category, _ = Category.objects.get_or_create(name="フード")
    return MenuItem.objects.create(category=category, name=name, price=price)


def register_kit(menu_item: MenuItem, initial_quantity: int = 5) -> Kit:
    return services.register_kit(
        Kit(menu_item_id=menu_item.id, name=f"{menu_item.name}キット"), initial_quantity
    )
