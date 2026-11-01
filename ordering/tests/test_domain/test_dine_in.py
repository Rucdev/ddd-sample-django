import uuid
from unittest import TestCase

from ordering.domain.entities import Bill, Order
from ordering.domain.events import OrderPickedUp, OrderPlaced
from ordering.domain.exceptions import (
    EmptyOrder,
    InvalidBillTransition,
    InvalidOrderTransition,
    SeatNotInUse,
)
from ordering.domain.value_objects import BillStatus, Money, OrderLine, OrderStatus, OrderType


def _line(name: str = "カフェラテ", price: int = 450, quantity: int = 1) -> OrderLine:
    return OrderLine(menu_item_id=uuid.uuid4(), name=name, unit_price=Money(price), quantity=quantity)


def _bill() -> Bill:
    return Bill.open(seat_id=uuid.uuid4(), seat_code="T1")


def _ready(order: Order) -> Order:
    for line_no in range(1, len(order.lines) + 1):
        order.start_cooking_line(line_no)
        order.complete_cooking_line(line_no)
    order.collect_events()
    return order


class PlaceAtSeatTests(TestCase):
    def test_dine_in_order_belongs_to_bill_without_customer(self) -> None:
        bill = _bill()

        order = Order.place_at_seat(bill=bill, lines=[_line()])

        self.assertEqual(order.order_type, OrderType.DINE_IN)
        self.assertEqual(order.bill_id, bill.id)
        self.assertIsNone(order.customer_id)
        self.assertEqual(order.status, OrderStatus.PLACED)

    def test_dine_in_order_has_no_discount(self) -> None:
        order = Order.place_at_seat(bill=_bill(), lines=[_line(price=500, quantity=2)])

        self.assertEqual(order.total, Money(1000))

    def test_dine_in_order_is_sent_to_kitchen_like_takeout(self) -> None:
        order = Order.place_at_seat(bill=_bill(), lines=[_line("スコーン", quantity=2)])

        (event,) = order.collect_events()

        assert isinstance(event, OrderPlaced)
        self.assertIsNone(event.customer_id)
        self.assertEqual(event.items[0].name, "スコーン")

    def test_cannot_order_on_paid_bill(self) -> None:
        bill = _bill()
        bill.settle()

        with self.assertRaises(SeatNotInUse):
            Order.place_at_seat(bill=bill, lines=[_line()])

    def test_cannot_place_empty_order(self) -> None:
        with self.assertRaises(EmptyOrder):
            Order.place_at_seat(bill=_bill(), lines=[])

    def test_owner_must_match_order_type(self) -> None:
        with self.assertRaises(ValueError):
            Order(order_id=uuid.uuid4(), lines=[_line()], order_type=OrderType.DINE_IN, customer_id=uuid.uuid4())
        with self.assertRaises(ValueError):
            Order(order_id=uuid.uuid4(), lines=[_line()], order_type=OrderType.TAKEOUT, bill_id=uuid.uuid4())


class ServeTests(TestCase):
    def test_ready_dine_in_order_is_served(self) -> None:
        order = _ready(Order.place_at_seat(bill=_bill(), lines=[_line()]))

        order.serve()

        self.assertEqual(order.status, OrderStatus.SERVED)
        self.assertEqual(order.collect_events(), [])  # 会員がいないのでポイント付与のイベントは出ない

    def test_cannot_serve_before_cooked(self) -> None:
        order = Order.place_at_seat(bill=_bill(), lines=[_line()])

        with self.assertRaises(InvalidOrderTransition):
            order.serve()

    def test_dine_in_order_is_not_picked_up(self) -> None:
        order = _ready(Order.place_at_seat(bill=_bill(), lines=[_line()]))

        with self.assertRaises(InvalidOrderTransition):
            order.pick_up()

    def test_takeout_order_is_not_served(self) -> None:
        order = _ready(Order.place(customer_id=uuid.uuid4(), lines=[_line()]))

        with self.assertRaises(InvalidOrderTransition):
            order.serve()
        order.pick_up()
        self.assertIsInstance(order.collect_events()[0], OrderPickedUp)


class BillTests(TestCase):
    def test_opened_bill_is_open(self) -> None:
        bill = _bill()

        self.assertEqual(bill.status, BillStatus.OPEN)
        self.assertEqual(bill.seat_code, "T1")

    def test_settle_marks_bill_paid(self) -> None:
        bill = _bill()

        bill.settle()

        self.assertEqual(bill.status, BillStatus.PAID)

    def test_cannot_settle_twice(self) -> None:
        bill = _bill()
        bill.settle()

        with self.assertRaises(InvalidBillTransition):
            bill.settle()

    def test_amount_due_sums_orders_except_cancelled_and_other_bills(self) -> None:
        bill = _bill()
        served = _ready(Order.place_at_seat(bill=bill, lines=[_line(price=450, quantity=2)]))
        served.serve()
        waiting = Order.place_at_seat(bill=bill, lines=[_line(price=300)])
        cancelled = Order.place_at_seat(bill=bill, lines=[_line(price=1000)])
        cancelled.cancel()
        other_seat = Order.place_at_seat(bill=_bill(), lines=[_line(price=5000)])

        self.assertEqual(bill.amount_due([served, waiting, cancelled, other_seat]), Money(1200))

    def test_amount_due_of_bill_without_orders_is_zero(self) -> None:
        self.assertEqual(_bill().amount_due([]), Money(0))
