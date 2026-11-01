import uuid

from django.test import TestCase

from kitchen.domain.events import CookingCompleted, CookingStarted
from menu.models import MenuItem
from ordering.application.dto import (
    CancelSeatOrderInput,
    PlaceOrderLineInput,
    PlaceSeatOrderInput,
    ServeOrderInput,
)
from ordering.application.queries import get_open_bill_for_seat, list_recently_paid_bills
from ordering.application.use_cases.cancel_seat_order import CancelSeatOrderUseCase
from ordering.application.use_cases.manage_bill import OpenBillUseCase, SettleBillUseCase
from ordering.application.use_cases.place_seat_order import PlaceSeatOrderUseCase
from ordering.application.use_cases.serve_order import ServeOrderUseCase
from ordering.domain.events import OrderPlaced
from ordering.domain.exceptions import (
    InvalidOrderTransition,
    MenuItemNotAvailable,
    OrderNotFound,
    SeatNotInUse,
)
from ordering.domain.value_objects import BillStatus, OrderStatus
from ordering.infrastructure.models import BillModel
from ordering.infrastructure.repositories import DjangoBillRepository, DjangoOrderRepository
from ordering.tests.test_application.factories import create_menu_item
from ordering.tests.test_application.fakes import FakeBillRepository, FakeOrderRepository
from seating.application.dto import SeatCommandInput
from seating.application.use_cases.apply_seat_layout import ApplySeatLayoutUseCase
from seating.application.use_cases.change_seat_status import OccupySeatUseCase, VacateSeatUseCase
from seating.infrastructure.repositories import DjangoAreaRepository, DjangoSeatRepository
from seating.tests.factories import layout, seat_spec
from shared.infrastructure import event_bus


class BillLifecycleUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.bills = FakeBillRepository()
        self.seat_id = uuid.uuid4()

    def test_open_bill_for_seat(self) -> None:
        OpenBillUseCase(self.bills).execute(self.seat_id, "T1")

        bill = self.bills.find_open_by_seat(self.seat_id)
        assert bill is not None
        self.assertEqual(bill.seat_code, "T1")

    def test_open_bill_twice_keeps_single_bill(self) -> None:
        OpenBillUseCase(self.bills).execute(self.seat_id, "T1")
        OpenBillUseCase(self.bills).execute(self.seat_id, "T1")

        self.assertEqual(len(self.bills.all()), 1)

    def test_settle_marks_open_bill_paid(self) -> None:
        OpenBillUseCase(self.bills).execute(self.seat_id, "T1")

        SettleBillUseCase(self.bills).execute(self.seat_id)

        self.assertIsNone(self.bills.find_open_by_seat(self.seat_id))
        self.assertEqual([b.status for b in self.bills.all()], [BillStatus.PAID])

    def test_settle_without_open_bill_does_nothing(self) -> None:
        SettleBillUseCase(self.bills).execute(self.seat_id)

        self.assertEqual(self.bills.all(), [])


class SeatOrderUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.latte = create_menu_item("カフェラテ", 450)
        self.orders = FakeOrderRepository()
        self.bills = FakeBillRepository()
        self.seat_id = uuid.uuid4()
        OpenBillUseCase(self.bills).execute(self.seat_id, "T1")

    def _place(self, seat_id: uuid.UUID | None = None, quantity: int = 1):
        return PlaceSeatOrderUseCase(self.orders, self.bills).execute(
            PlaceSeatOrderInput(
                seat_id=seat_id or self.seat_id,
                lines=(PlaceOrderLineInput(menu_item_id=self.latte.id, quantity=quantity),),
            )
        )

    def _ready(self, order_id: uuid.UUID) -> None:
        order = self.orders.find_by_id(order_id)
        assert order is not None
        order.start_cooking_line(1)
        order.complete_cooking_line(1)
        self.orders.save(order)

    def test_seat_order_is_attached_to_open_bill(self) -> None:
        result = self._place(quantity=2)

        bill = self.bills.find_open_by_seat(self.seat_id)
        assert bill is not None
        self.assertEqual(result.order_type, "DINE_IN")
        self.assertEqual(result.bill_id, bill.id)
        self.assertIsNone(result.customer_id)
        self.assertEqual(result.total, 900)

    def test_seat_order_publishes_order_placed(self) -> None:
        received: list[OrderPlaced] = []
        with event_bus.isolated_subscribers():
            event_bus.subscribe(OrderPlaced, received.append)
            self._place()

        self.assertEqual(len(received), 1)
        self.assertIsNone(received[0].customer_id)

    def test_cannot_order_from_seat_without_open_bill(self) -> None:
        with self.assertRaises(SeatNotInUse):
            self._place(seat_id=uuid.uuid4())

    def test_cannot_order_after_seat_is_vacated(self) -> None:
        SettleBillUseCase(self.bills).execute(self.seat_id)

        with self.assertRaises(SeatNotInUse):
            self._place()

    def test_cannot_order_unavailable_item(self) -> None:
        self.latte.status = MenuItem.Status.SOLD_OUT
        self.latte.save()

        with self.assertRaises(MenuItemNotAvailable):
            self._place()

    def test_serve_ready_order(self) -> None:
        order = self._place()
        self._ready(order.id)

        result = ServeOrderUseCase(self.orders).execute(ServeOrderInput(order.id))

        self.assertEqual(result.status, "SERVED")

    def test_serve_before_ready_is_rejected(self) -> None:
        order = self._place()

        with self.assertRaises(InvalidOrderTransition):
            ServeOrderUseCase(self.orders).execute(ServeOrderInput(order.id))

    def test_serve_unknown_order(self) -> None:
        with self.assertRaises(OrderNotFound):
            ServeOrderUseCase(self.orders).execute(ServeOrderInput(uuid.uuid4()))

    def test_cancel_own_seat_order(self) -> None:
        order = self._place()

        result = CancelSeatOrderUseCase(self.orders, self.bills).execute(
            CancelSeatOrderInput(seat_id=self.seat_id, order_id=order.id)
        )

        self.assertEqual(result.status, "CANCELLED")

    def test_cannot_cancel_order_of_another_seat(self) -> None:
        order = self._place()
        other_seat = uuid.uuid4()
        OpenBillUseCase(self.bills).execute(other_seat, "T2")

        with self.assertRaises(OrderNotFound):
            CancelSeatOrderUseCase(self.orders, self.bills).execute(
                CancelSeatOrderInput(seat_id=other_seat, order_id=order.id)
            )

    def test_cannot_cancel_after_bill_is_paid(self) -> None:
        order = self._place()
        SettleBillUseCase(self.bills).execute(self.seat_id)

        with self.assertRaises(SeatNotInUse):
            CancelSeatOrderUseCase(self.orders, self.bills).execute(
                CancelSeatOrderInput(seat_id=self.seat_id, order_id=order.id)
            )


class DineInFlowIntegrationTests(TestCase):
    """本番の配線(apps.py の ready() で登録された購読)を通して、席の案内 → 席からの注文 →
    調理 → 提供待ち → 提供完了 → 退席で支払済 → 再度の案内で別の会計、がつながることを確かめる。
    キッチンの調理は kitchen のイベントを発行して進める(ordering のテストからは kitchen の
    内部に触れない)。チケットが作られることは kitchen 側の結合テストで確かめている。
    """

    def setUp(self) -> None:
        ApplySeatLayoutUseCase(DjangoSeatRepository(), DjangoAreaRepository()).execute(
            layout(seat_spec("T1"))
        )
        self.seat = DjangoSeatRepository().find_all()[0]
        self.latte = create_menu_item("カフェラテ", 450)

    def _occupy(self) -> None:
        OccupySeatUseCase(DjangoSeatRepository()).execute(SeatCommandInput(self.seat.id))

    def _vacate(self) -> None:
        VacateSeatUseCase(DjangoSeatRepository()).execute(SeatCommandInput(self.seat.id))

    def _place(self, quantity: int = 1):
        return PlaceSeatOrderUseCase(DjangoOrderRepository(), DjangoBillRepository()).execute(
            PlaceSeatOrderInput(
                seat_id=self.seat.id,
                lines=(PlaceOrderLineInput(menu_item_id=self.latte.id, quantity=quantity),),
            )
        )

    def _cook(self, order_id: uuid.UUID) -> None:
        event_bus.publish(
            [
                CookingStarted(ticket_id=uuid.uuid4(), order_id=order_id, line_no=1),
                CookingCompleted(ticket_id=uuid.uuid4(), order_id=order_id, line_no=1),
            ]
        )

    def test_occupying_a_seat_opens_its_bill(self) -> None:
        self.assertIsNone(get_open_bill_for_seat(self.seat.id))

        self._occupy()

        bill = get_open_bill_for_seat(self.seat.id)
        assert bill is not None
        self.assertEqual(bill.seat_code, "T1")

    def test_full_dine_in_flow(self) -> None:
        self._occupy()
        first = self._place(quantity=2)
        second = self._place(quantity=1)

        self._cook(first.id)
        bill = get_open_bill_for_seat(self.seat.id)
        assert bill is not None
        self.assertEqual([o.status for o in bill.orders], ["READY", "PLACED"])  # READY = 提供待ち

        ServeOrderUseCase(DjangoOrderRepository()).execute(ServeOrderInput(first.id))
        bill = get_open_bill_for_seat(self.seat.id)
        assert bill is not None
        self.assertEqual(bill.orders[0].status, OrderStatus.SERVED.value)
        self.assertEqual(bill.amount_due, 1350)  # 会計は明細としてキープされ、まとめて払う

        self._vacate()

        self.assertIsNone(get_open_bill_for_seat(self.seat.id))
        (paid,) = list_recently_paid_bills()
        self.assertEqual(paid.status, "PAID")
        self.assertEqual(paid.amount_due, 1350)
        self.assertEqual(len(paid.orders), 2)

    def test_reusing_the_seat_opens_a_new_bill(self) -> None:
        self._occupy()
        self._place()
        self._vacate()

        self._occupy()

        bill = get_open_bill_for_seat(self.seat.id)
        assert bill is not None
        self.assertEqual(bill.orders, ())
        self.assertEqual(bill.amount_due, 0)
        self.assertEqual(BillModel.objects.filter(seat_id=self.seat.id).count(), 2)

    def test_cannot_order_from_vacated_seat(self) -> None:
        self._occupy()
        self._vacate()

        with self.assertRaises(SeatNotInUse):
            self._place()
