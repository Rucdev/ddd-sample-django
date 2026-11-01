import uuid

from django.test import TestCase

from ordering.application.dto import CancelOrderInput, PickUpOrderInput
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.complete_line_cooking import CompleteLineCookingUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.start_line_cooking import StartLineCookingUseCase
from ordering.domain.events import OrderCancelled, OrderPickedUp
from ordering.domain.exceptions import InvalidOrderTransition, OrderNotFound
from ordering.domain.value_objects import OrderStatus
from ordering.tests.test_application.factories import make_order
from ordering.tests.test_application.fakes import FakeOrderRepository
from shared.infrastructure import event_bus


# 注文後のユースケースは他モジュールに照会しないので、前提データの準備はフェイク
# リポジトリに Order を入れるだけで済む(TestCase なのはユースケースが
# transaction.atomic() を張るため)。


class OrderLifecycleUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.repository = FakeOrderRepository()
        self.order = make_order(uuid.uuid4(), price=500, quantity=2)
        self.repository.save(self.order)

    def _status(self) -> OrderStatus:
        order = self.repository.find_by_id(self.order.id)
        assert order is not None
        return order.status

    def test_line_cooking_moves_order_to_preparing_then_ready(self) -> None:
        StartLineCookingUseCase(self.repository).execute(self.order.id, 1)
        self.assertEqual(self._status(), OrderStatus.PREPARING)

        CompleteLineCookingUseCase(self.repository).execute(self.order.id, 1)
        self.assertEqual(self._status(), OrderStatus.READY)

    def test_pick_up_publishes_event(self) -> None:
        StartLineCookingUseCase(self.repository).execute(self.order.id, 1)
        CompleteLineCookingUseCase(self.repository).execute(self.order.id, 1)
        received = []
        event_bus.subscribe(OrderPickedUp, received.append)
        self.addCleanup(event_bus.unsubscribe, OrderPickedUp, received.append)

        result = PickUpOrderUseCase(self.repository).execute(PickUpOrderInput(self.order.id))

        self.assertEqual(result.status, "PICKED_UP")
        self.assertEqual([e.total for e in received], [1000])

    def test_pick_up_before_ready_raises(self) -> None:
        with self.assertRaises(InvalidOrderTransition):
            PickUpOrderUseCase(self.repository).execute(PickUpOrderInput(self.order.id))

    def test_cancel_publishes_event(self) -> None:
        received = []
        event_bus.subscribe(OrderCancelled, received.append)
        self.addCleanup(event_bus.unsubscribe, OrderCancelled, received.append)

        result = CancelOrderUseCase(self.repository).execute(CancelOrderInput(self.order.id))

        self.assertEqual(result.status, "CANCELLED")
        self.assertEqual(len(received), 1)

    def test_cancel_after_preparing_started_raises(self) -> None:
        StartLineCookingUseCase(self.repository).execute(self.order.id, 1)

        with self.assertRaises(InvalidOrderTransition):
            CancelOrderUseCase(self.repository).execute(CancelOrderInput(self.order.id))
        self.assertEqual(self._status(), OrderStatus.PREPARING)

    def test_unknown_order_raises_not_found(self) -> None:
        with self.assertRaises(OrderNotFound):
            CancelOrderUseCase(self.repository).execute(CancelOrderInput(uuid.uuid4()))
        with self.assertRaises(OrderNotFound):
            PickUpOrderUseCase(self.repository).execute(PickUpOrderInput(uuid.uuid4()))
        with self.assertRaises(OrderNotFound):
            StartLineCookingUseCase(self.repository).execute(uuid.uuid4(), 1)
