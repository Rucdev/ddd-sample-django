import uuid

from django.test import TestCase

from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.use_cases.cancel_ticket import CancelTicketUseCase
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.open_ticket import OpenTicketUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.domain.entities import Ticket
from kitchen.domain.events import CookingStarted
from kitchen.domain.exceptions import InvalidTicketTransition, TicketNotFound
from kitchen.domain.value_objects import TicketItem, TicketStatus
from kitchen.tests.test_application.fakes import FakeTicketRepository
from shared.infrastructure import event_bus


class KitchenUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.repository = FakeTicketRepository()
        self.order_id = uuid.uuid4()
        OpenTicketUseCase(self.repository).execute(
            order_id=self.order_id, items=[TicketItem(name="カフェラテ", quantity=1)]
        )
        ticket = self.repository.find_by_order(self.order_id)
        assert ticket is not None
        self.ticket = ticket

    def _find_ticket(self) -> Ticket:
        ticket = self.repository.find_by_order(self.order_id)
        assert ticket is not None
        return ticket

    def test_open_ticket_is_idempotent_per_order(self) -> None:
        OpenTicketUseCase(self.repository).execute(
            order_id=self.order_id, items=[TicketItem(name="別の商品", quantity=1)]
        )

        self.assertEqual(self._find_ticket().id, self.ticket.id)

    def test_start_cooking_publishes_event(self) -> None:
        # このテストは kitchen 単体の確認なので、ordering 側の本物のハンドラ(注文の
        # ステータス更新)が動かないよう購読を外しておく。
        from ordering.infrastructure.event_handlers import handle_cooking_started

        event_bus.unsubscribe(CookingStarted, handle_cooking_started)
        self.addCleanup(event_bus.subscribe, CookingStarted, handle_cooking_started)
        received = []
        event_bus.subscribe(CookingStarted, received.append)
        self.addCleanup(event_bus.unsubscribe, CookingStarted, received.append)

        result = StartCookingUseCase(self.repository).execute(StartCookingInput(self.ticket.id))

        self.assertEqual(result.status, "COOKING")
        self.assertEqual([e.order_id for e in received], [self.order_id])

    def test_complete_before_start_raises(self) -> None:
        with self.assertRaises(InvalidTicketTransition):
            CompleteCookingUseCase(self.repository).execute(CompleteCookingInput(self.ticket.id))

    def test_cancel_ticket_by_order(self) -> None:
        CancelTicketUseCase(self.repository).execute(order_id=self.order_id)

        self.assertEqual(self._find_ticket().status, TicketStatus.CANCELLED)

    def test_cancel_ticket_for_unknown_order_is_a_no_op(self) -> None:
        CancelTicketUseCase(self.repository).execute(order_id=uuid.uuid4())  # should not raise

    def test_unknown_ticket_raises_not_found(self) -> None:
        with self.assertRaises(TicketNotFound):
            StartCookingUseCase(self.repository).execute(StartCookingInput(uuid.uuid4()))
