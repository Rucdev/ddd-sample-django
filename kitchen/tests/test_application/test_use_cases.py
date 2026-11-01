import uuid

from django.test import TestCase

from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.use_cases.cancel_tickets import CancelTicketsUseCase
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.open_tickets import OpenTicketsUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.domain.events import CookingStarted
from kitchen.domain.exceptions import InvalidTicketTransition, TicketNotFound
from kitchen.domain.value_objects import TicketItem, TicketStatus
from kitchen.tests.test_application.fakes import FakeTicketRepository
from shared.infrastructure import event_bus


class KitchenUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.repository = FakeTicketRepository()
        self.order_id = uuid.uuid4()
        OpenTicketsUseCase(self.repository).execute(
            order_id=self.order_id,
            items=[(1, TicketItem(name="カフェラテ", quantity=2)), (2, TicketItem(name="スコーン", quantity=1))],
        )
        self.latte, self.scone = self.repository.find_by_order(self.order_id)

    def _without_ordering_handler(self) -> list:
        # kitchen 単体の確認なので、ordering 側の本物のハンドラ(注文の明細の更新)が
        # 動かないよう購読を外し、代わりに受け取ったイベントを記録する。
        from ordering.infrastructure.event_handlers import handle_cooking_started

        event_bus.unsubscribe(CookingStarted, handle_cooking_started)
        self.addCleanup(event_bus.subscribe, CookingStarted, handle_cooking_started)
        received: list = []
        event_bus.subscribe(CookingStarted, received.append)
        self.addCleanup(event_bus.unsubscribe, CookingStarted, received.append)
        return received

    def test_one_ticket_per_order_line(self) -> None:
        self.assertEqual(
            [(t.line_no, t.item.name, t.item.quantity) for t in (self.latte, self.scone)],
            [(1, "カフェラテ", 2), (2, "スコーン", 1)],
        )

    def test_open_tickets_is_idempotent_per_order(self) -> None:
        OpenTicketsUseCase(self.repository).execute(
            order_id=self.order_id, items=[(1, TicketItem(name="別の商品", quantity=1))]
        )

        self.assertEqual(len(self.repository.find_by_order(self.order_id)), 2)

    def test_tickets_of_one_order_progress_independently(self) -> None:
        received = self._without_ordering_handler()

        result = StartCookingUseCase(self.repository).execute(StartCookingInput(self.scone.id))

        self.assertEqual(result.status, "COOKING")
        self.assertEqual([(e.order_id, e.line_no) for e in received], [(self.order_id, 2)])
        latte = self.repository.find_by_id(self.latte.id)
        assert latte is not None
        self.assertEqual(latte.status, TicketStatus.QUEUED)

    def test_complete_before_start_raises(self) -> None:
        with self.assertRaises(InvalidTicketTransition):
            CompleteCookingUseCase(self.repository).execute(CompleteCookingInput(self.latte.id))

    def test_cancel_cancels_every_ticket_of_the_order(self) -> None:
        CancelTicketsUseCase(self.repository).execute(order_id=self.order_id)

        self.assertEqual(
            [t.status for t in self.repository.find_by_order(self.order_id)],
            [TicketStatus.CANCELLED, TicketStatus.CANCELLED],
        )

    def test_cancel_for_unknown_order_is_a_no_op(self) -> None:
        CancelTicketsUseCase(self.repository).execute(order_id=uuid.uuid4())  # should not raise

    def test_unknown_ticket_raises_not_found(self) -> None:
        with self.assertRaises(TicketNotFound):
            StartCookingUseCase(self.repository).execute(StartCookingInput(uuid.uuid4()))
