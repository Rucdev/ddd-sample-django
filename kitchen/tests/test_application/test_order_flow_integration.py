"""本番の配線そのもの(各モジュールの apps.py の ready() で登録された購読)を通して、
注文 → 調理 → 受取 → ポイント付与までがモジュールをまたいでつながることを確かめる。
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
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.domain.exceptions import InvalidOrderTransition
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import create_customer, create_menu_item


class OrderFlowIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.customer = create_customer(rank=Customer.Rank.GOLD)
        self.latte = create_menu_item("カフェラテ", 450)
        self.orders = DjangoOrderRepository()
        self.tickets = DjangoTicketRepository()

        self.order = PlaceOrderUseCase(self.orders).execute(
            PlaceOrderInput(
                customer_id=self.customer.id,
                lines=(PlaceOrderLineInput(menu_item_id=self.latte.id, quantity=3),),
            )
        )
        ticket = self.tickets.find_by_order(self.order.id)
        # 注文と同時にチケットが作られていることは、ここで確かめておく。
        assert ticket is not None
        self.ticket = ticket

    def _order_status(self) -> str:
        order = self.orders.find_by_id(self.order.id)
        assert order is not None
        return order.status

    def test_placing_an_order_opens_a_ticket(self) -> None:
        self.assertEqual([(i.name, i.quantity) for i in self.ticket.items], [("カフェラテ", 3)])

    def test_full_flow_from_cooking_to_points(self) -> None:
        StartCookingUseCase(self.tickets).execute(StartCookingInput(self.ticket.id))
        self.assertEqual(self._order_status(), "PREPARING")

        CompleteCookingUseCase(self.tickets).execute(CompleteCookingInput(self.ticket.id))
        self.assertEqual(self._order_status(), "READY")

        PickUpOrderUseCase(self.orders).execute(PickUpOrderInput(self.order.id))
        self.assertEqual(self._order_status(), "PICKED_UP")

        # 1,350 円 - 10%(135 円)= 1,215 円 → 12 ポイント
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 12)

    def test_cancelling_an_order_cancels_the_ticket(self) -> None:
        CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))

        self.assertEqual(TicketModel.objects.get(id=self.ticket.id).status, "CANCELLED")

    def test_cannot_cancel_once_cooking_started(self) -> None:
        StartCookingUseCase(self.tickets).execute(StartCookingInput(self.ticket.id))

        with self.assertRaises(InvalidOrderTransition):
            CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))
        self.assertEqual(TicketModel.objects.get(id=self.ticket.id).status, "COOKING")

    def test_cooking_a_cancelled_order_is_rejected(self) -> None:
        CancelOrderUseCase(self.orders).execute(CancelOrderInput(self.order.id))

        with self.assertRaises(InvalidTicketTransition):
            StartCookingUseCase(self.tickets).execute(StartCookingInput(self.ticket.id))
