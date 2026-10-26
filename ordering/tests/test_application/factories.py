"""テスト用のデータ作成ヘルパ。他モジュール(menu・customers)の前提データは、テストに
限って ORM モデルを直接使って作る(import-linter の ignore_imports で許可している)。
"""

import uuid

from customers.models import Customer
from menu.models import Category, MenuItem
from ordering.domain.entities import Order
from ordering.domain.value_objects import DiscountRate, Money, OrderLine


def create_customer(**kwargs) -> Customer:
    kwargs.setdefault("name", "Alice")
    kwargs.setdefault("email", f"{uuid.uuid4().hex[:8]}@example.com")
    return Customer.objects.create(**kwargs)


def create_menu_item(name: str = "カフェラテ", price: int = 450, **kwargs) -> MenuItem:
    category, _ = Category.objects.get_or_create(name="ドリンク")
    return MenuItem.objects.create(category=category, name=name, price=price, **kwargs)


def make_order(customer_id: uuid.UUID, *, price: int = 450, quantity: int = 1) -> Order:
    """DB を介さずに `Order` エンティティを作る。発行済みイベントは捨てておく。"""
    order = Order.place(
        customer_id=customer_id,
        lines=[
            OrderLine(
                menu_item_id=uuid.uuid4(), name="カフェラテ", unit_price=Money(price), quantity=quantity
            )
        ],
        discount_rate=DiscountRate(0),
    )
    order.collect_events()
    return order
