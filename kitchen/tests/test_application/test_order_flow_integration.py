"""本番の配線そのもの(各モジュールの apps.py の ready() で登録された購読)を通して、
注文 → 明細ごとの調理 → 受取 → ポイント付与までがモジュールをまたいでつながることを確かめる。
テスト内で subscribe / mock を差し込まない。
"""

from django.test import TestCase

from customers.models import Customer
from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.domain.exceptions import InvalidTicketTransition
from kitchen.infrastructure.models import TicketModel
from kitchen.infrastructure.repositories import DjangoTicketRepository
from ordering.application.dto import (
    CancelOrderInput,
    PickUpOrderInput,
    PlaceOrderInput,
    PlaceOrderLineInput,
)
from ordering.application.queries import get_order
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.domain.exceptions import InvalidOrderTransition
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import create_customer, create_menu_item


class OrderFlowIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.customer = create_customer(rank=Customer.Rank.GOLD)
        latte = create_menu_item("カフェラテ", 450)
        sandwich = create_menu_item("ホットサンド", 650)
        self.orders = DjangoOrderRepository()
        self.tickets = DjangoTicketRepository()

        self.order = PlaceOrderUseCase(self.orders).execute(
            PlaceOrderInput(
                customer_id=self.customer.id,
                lines=(
                    PlaceOrderLineInput(menu_item_id=latte.id, quantity=3),
                    PlaceOrderLineInput(menu_item_id=sandwich.id, quantity=1),
                ),
            )
        )
        # 注文と同時に、明細ごとのチケットが作られている
        self.latte_ticket, self.sandwich_ticket = self.tickets.find_by_order(self.order.id)

    def _order(self):
        order = get_order(self.order.id)
        assert order is not None
        return order

    def _cook(self, ticket) -> None:
        StartCookingUseCase(self.tickets).execute(StartCookingInput(ticket.id))
        CompleteCookingUseCase(self.tickets).execute(CompleteCookingInput(ticket.id))

    def test_placing_an_order_opens_a_ticket_per_line(self) -> None:
        self.assertEqual(
            [(t.line_no, t.item.name, t.item.quantity) for t in (self.latte_ticket, self.sandwich_ticket)],
            [(1, "カフェラテ", 3), (2, "ホットサンド", 1)],
        )

    def test_order_is_ready_only_after_every_line_is_cooked(self) -> None:
        StartCookingUseCase(self.tickets).execute(StartCookingInput(self.sandwich_ticket.id))
        self.assertEqual(self._order().status, "PREPARING")
        self.assertEqual([l.cooking_status for l in self._order().lines], ["WAITING", "COOKING"])

        # ドリンクは後から始めて先に終わってもよい
        self._cook(self.latte_ticket)
        self.assertEqual(self._order().status, "PREPARING")
        self.assertEqual(self._order().cooked_line_count, 1)

        CompleteCookingUseCase(self.tickets).execute(CompleteCookingInput(self.sandwich_ticket.id))
        self.assertEqual(self._order().status, "READY")

    def test_full_flow_from_cooking_to_points(self) -> None:
        self._cook(self.latte_ticket)
        self._cook(self.sandwich_ticket)

        PickUpOrderUseCase(self.orders).execute(PickUpOrderInput(self.order.id))
        self.assertEqual(self._order().status, "PICKED_UP")

        # (1,350 + 650) 円 - 10%(200 円)= 1,800 円 → 18 ポイント
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 18)

    def test_cancelling_an_order_cancels_every_ticket(self) -> None:
        CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))

        self.assertEqual(
            list(TicketModel.objects.filter(order_id=self.order.id).values_list("status", flat=True)),
            ["CANCELLED", "CANCELLED"],
        )

    def test_cannot_cancel_once_any_line_started(self) -> None:
        StartCookingUseCase(self.tickets).execute(StartCookingInput(self.sandwich_ticket.id))

        with self.assertRaises(InvalidOrderTransition):
            CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))
        self.assertEqual(TicketModel.objects.get(id=self.latte_ticket.id).status, "QUEUED")

    def test_cooking_a_cancelled_order_is_rejected(self) -> None:
        CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))

        with self.assertRaises(InvalidTicketTransition):
            StartCookingUseCase(self.tickets).execute(StartCookingInput(self.latte_ticket.id))
