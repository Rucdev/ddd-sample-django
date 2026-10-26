import uuid

from django.test import TestCase

from customers.models import Customer
from menu.models import MenuItem
from ordering.application.dto import PlaceOrderInput, PlaceOrderLineInput
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.domain.events import OrderPlaced
from ordering.domain.exceptions import (
    CustomerNotEligible,
    EmptyOrder,
    InvalidQuantity,
    MenuItemNotAvailable,
    TooManyInProgressOrders,
)
from ordering.domain.services import MAX_IN_PROGRESS_ORDERS
from ordering.tests.test_application.factories import create_customer, create_menu_item, make_order
from ordering.tests.test_application.fakes import FakeOrderRepository
from shared.infrastructure import event_bus


class PlaceOrderUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.customer = create_customer()
        self.latte = create_menu_item("カフェラテ", 450)
        self.scone = create_menu_item("スコーン", 300)

        self.repository = FakeOrderRepository()
        self.use_case = PlaceOrderUseCase(order_repository=self.repository)

    def _input(self, *lines: tuple, customer_id: uuid.UUID | None = None) -> PlaceOrderInput:
        return PlaceOrderInput(
            customer_id=customer_id or self.customer.id,
            lines=tuple(PlaceOrderLineInput(menu_item_id=i, quantity=q) for i, q in lines),
        )

    def test_places_order_with_menu_snapshot(self) -> None:
        result = self.use_case.execute(self._input((self.latte.id, 2), (self.scone.id, 1)))

        self.assertEqual(result.status, "PLACED")
        self.assertEqual([line.name for line in result.lines], ["カフェラテ", "スコーン"])
        self.assertEqual(result.total, 1200)
        self.assertIsNotNone(self.repository.find_by_id(result.id))

    def test_price_change_after_order_does_not_affect_order(self) -> None:
        result = self.use_case.execute(self._input((self.latte.id, 1)))

        self.latte.price = 999
        self.latte.save()

        order = self.repository.find_by_id(result.id)
        assert order is not None
        self.assertEqual(order.total.amount, 450)

    def test_publishes_order_placed_event(self) -> None:
        received = []
        event_bus.subscribe(OrderPlaced, received.append)
        self.addCleanup(event_bus.unsubscribe, OrderPlaced, received.append)

        self.use_case.execute(self._input((self.latte.id, 1)))

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].customer_id, self.customer.id)

    def test_silver_customer_gets_5_percent_off(self) -> None:
        self.customer.rank = Customer.Rank.SILVER
        self.customer.save()

        result = self.use_case.execute(self._input((self.latte.id, 2)))

        self.assertEqual((result.subtotal, result.discount, result.total), (900, 45, 855))

    def test_gold_customer_gets_10_percent_off(self) -> None:
        self.customer.rank = Customer.Rank.GOLD
        self.customer.save()

        result = self.use_case.execute(self._input((self.latte.id, 2)))

        self.assertEqual((result.subtotal, result.discount, result.total), (900, 90, 810))

    def test_rejects_unknown_customer(self) -> None:
        with self.assertRaises(CustomerNotEligible):
            self.use_case.execute(self._input((self.latte.id, 1), customer_id=uuid.uuid4()))

    def test_rejects_suspended_customer(self) -> None:
        self.customer.status = Customer.Status.SUSPENDED
        self.customer.save()

        with self.assertRaises(CustomerNotEligible):
            self.use_case.execute(self._input((self.latte.id, 1)))

    def test_rejects_unknown_menu_item(self) -> None:
        with self.assertRaises(MenuItemNotAvailable):
            self.use_case.execute(self._input((uuid.uuid4(), 1)))

    def test_rejects_sold_out_menu_item(self) -> None:
        self.latte.status = MenuItem.Status.SOLD_OUT
        self.latte.save()

        with self.assertRaises(MenuItemNotAvailable):
            self.use_case.execute(self._input((self.latte.id, 1)))

    def test_rejects_empty_order(self) -> None:
        with self.assertRaises(EmptyOrder):
            self.use_case.execute(self._input())

    def test_rejects_too_large_quantity(self) -> None:
        with self.assertRaises(InvalidQuantity):
            self.use_case.execute(self._input((self.latte.id, 11)))

    def test_rejects_when_too_many_orders_in_progress(self) -> None:
        for _ in range(MAX_IN_PROGRESS_ORDERS):
            self.repository.save(make_order(self.customer.id))

        with self.assertRaises(TooManyInProgressOrders):
            self.use_case.execute(self._input((self.latte.id, 1)))

    def test_picked_up_orders_do_not_count_as_in_progress(self) -> None:
        for _ in range(MAX_IN_PROGRESS_ORDERS):
            order = make_order(self.customer.id)
            order.start_preparing()
            order.mark_ready()
            order.pick_up()
            self.repository.save(order)

        result = self.use_case.execute(self._input((self.latte.id, 1)))

        self.assertEqual(result.status, "PLACED")
