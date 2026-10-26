import uuid
from unittest import TestCase

from ordering.domain.entities import Order
from ordering.domain.events import OrderCancelled, OrderedItem, OrderPickedUp, OrderPlaced
from ordering.domain.exceptions import EmptyOrder, InvalidOrderTransition
from ordering.domain.value_objects import DiscountRate, Money, OrderLine, OrderStatus


def _line(name: str = "カフェラテ", price: int = 450, quantity: int = 1) -> OrderLine:
    return OrderLine(
        menu_item_id=uuid.uuid4(), name=name, unit_price=Money(price), quantity=quantity
    )


def _make_order(*lines: OrderLine, discount_rate: DiscountRate = DiscountRate(0)) -> Order:
    return Order.place(
        customer_id=uuid.uuid4(), lines=lines or [_line()], discount_rate=discount_rate
    )


def _ready_order() -> Order:
    order = _make_order()
    order.start_preparing()
    order.mark_ready()
    order.collect_events()
    return order


class OrderPlaceTests(TestCase):
    def test_place_starts_in_placed_status(self) -> None:
        self.assertEqual(_make_order().status, OrderStatus.PLACED)

    def test_place_without_lines_raises(self) -> None:
        with self.assertRaises(EmptyOrder):
            Order.place(customer_id=uuid.uuid4(), lines=[])

    def test_place_records_order_placed_event_with_items(self) -> None:
        order = _make_order(_line("カフェラテ", quantity=2), _line("スコーン", price=300))

        events = order.collect_events()

        self.assertEqual(len(events), 1)
        event = events[0]
        assert isinstance(event, OrderPlaced)
        self.assertEqual(event.order_id, order.id)
        self.assertEqual(
            event.items,
            (OrderedItem(name="カフェラテ", quantity=2), OrderedItem(name="スコーン", quantity=1)),
        )


class OrderAmountTests(TestCase):
    def test_amounts_without_discount(self) -> None:
        order = _make_order(_line(price=450, quantity=2), _line(price=300, quantity=1))

        self.assertEqual(order.subtotal, Money(1200))
        self.assertEqual(order.discount, Money(0))
        self.assertEqual(order.total, Money(1200))

    def test_amounts_with_discount(self) -> None:
        order = _make_order(_line(price=450, quantity=2), discount_rate=DiscountRate(10))

        self.assertEqual(order.subtotal, Money(900))
        self.assertEqual(order.discount, Money(90))
        self.assertEqual(order.total, Money(810))


class OrderTransitionTests(TestCase):
    def test_happy_path_to_picked_up(self) -> None:
        order = _make_order()

        order.start_preparing()
        self.assertEqual(order.status, OrderStatus.PREPARING)
        order.mark_ready()
        self.assertEqual(order.status, OrderStatus.READY)
        order.pick_up()
        self.assertEqual(order.status, OrderStatus.PICKED_UP)

    def test_pick_up_records_event_with_total(self) -> None:
        order = _make_order(_line(price=500, quantity=2), discount_rate=DiscountRate(10))
        order.start_preparing()
        order.mark_ready()
        order.collect_events()

        order.pick_up()
        events = order.collect_events()

        self.assertEqual(len(events), 1)
        event = events[0]
        assert isinstance(event, OrderPickedUp)
        self.assertEqual(event.total, 900)

    def test_cannot_pick_up_before_ready(self) -> None:
        order = _make_order()

        with self.assertRaises(InvalidOrderTransition):
            order.pick_up()

    def test_cannot_pick_up_twice(self) -> None:
        order = _ready_order()
        order.pick_up()

        with self.assertRaises(InvalidOrderTransition):
            order.pick_up()

    def test_cannot_mark_ready_before_preparing(self) -> None:
        order = _make_order()

        with self.assertRaises(InvalidOrderTransition):
            order.mark_ready()


class OrderCancelTests(TestCase):
    def test_cancel_placed_order(self) -> None:
        order = _make_order()
        order.collect_events()

        order.cancel()

        self.assertEqual(order.status, OrderStatus.CANCELLED)
        events = order.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], OrderCancelled)

    def test_cannot_cancel_once_preparing(self) -> None:
        order = _make_order()
        order.start_preparing()

        with self.assertRaises(InvalidOrderTransition):
            order.cancel()

    def test_cannot_cancel_ready_order(self) -> None:
        with self.assertRaises(InvalidOrderTransition):
            _ready_order().cancel()

    def test_cancelled_order_cannot_start_preparing(self) -> None:
        order = _make_order()
        order.cancel()

        with self.assertRaises(InvalidOrderTransition):
            order.start_preparing()
