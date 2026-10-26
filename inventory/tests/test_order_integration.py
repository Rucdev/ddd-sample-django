"""ordering の注文・キャンセルと在庫の連携。PlaceOrderUseCase → inventory.public、
OrderCancelled → inventory の購読、までを実際の配線で通す。
"""

from django.test import TestCase

from customers.models import Customer
from inventory.models import Kit
from inventory.tests.helpers import create_menu_item, register_kit
from ordering.application.dto import CancelOrderInput, PlaceOrderInput, PlaceOrderLineInput
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.domain.exceptions import MenuItemNotAvailable, OutOfStock
from ordering.infrastructure.models import OrderModel
from ordering.infrastructure.repositories import DjangoOrderRepository


class OrderStockIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.customer = Customer.objects.create(name="Alice", email="alice@example.com")
        self.sandwich = create_menu_item("ホットサンド", 600)
        self.coffee = create_menu_item("ドリップコーヒー", 350)  # キット無し
        self.kit = register_kit(self.sandwich, initial_quantity=2)

    def _place(self, *lines):
        return PlaceOrderUseCase(order_repository=DjangoOrderRepository()).execute(
            PlaceOrderInput(
                customer_id=self.customer.id,
                lines=tuple(PlaceOrderLineInput(menu_item_id=i.id, quantity=q) for i, q in lines),
            )
        )

    def _on_hand(self) -> int:
        return Kit.objects.get(pk=self.kit.pk).on_hand

    def test_order_consumes_kits(self) -> None:
        self._place((self.sandwich, 1), (self.coffee, 5))

        self.assertEqual(self._on_hand(), 1)

    def test_order_beyond_stock_is_rejected_and_nothing_is_saved(self) -> None:
        with self.assertRaises(OutOfStock) as ctx:
            self._place((self.sandwich, 3))

        self.assertEqual(ctx.exception.menu_item_id, self.sandwich.id)
        self.assertEqual(self._on_hand(), 2)
        self.assertFalse(OrderModel.objects.exists())

    def test_item_becomes_unorderable_when_stock_runs_out(self) -> None:
        self._place((self.sandwich, 2))

        with self.assertRaises(MenuItemNotAvailable):
            self._place((self.sandwich, 1))

    def test_cancel_returns_kits(self) -> None:
        order = self._place((self.sandwich, 2))

        CancelOrderUseCase(order_repository=DjangoOrderRepository()).execute(
            CancelOrderInput(order_id=order.id)
        )

        self.assertEqual(self._on_hand(), 2)
        self.sandwich.refresh_from_db()
        self.assertFalse(self.sandwich.out_of_stock)
