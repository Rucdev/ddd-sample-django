import uuid

from django.test import TestCase

from ordering.domain.value_objects import OrderStatus
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import make_order


class DjangoOrderRepositoryTests(TestCase):
    """ORM ⇔ エンティティの変換で値が欠けないことの確認(往復させて比べる)。"""

    def setUp(self) -> None:
        self.repository = DjangoOrderRepository()

    def test_round_trip_keeps_lines_and_amounts(self) -> None:
        order = make_order(uuid.uuid4(), price=450, quantity=3)

        self.repository.save(order)
        loaded = self.repository.find_by_id(order.id)

        assert loaded is not None
        self.assertEqual(loaded.lines, order.lines)
        self.assertEqual(loaded.total, order.total)
        self.assertEqual(loaded.status, OrderStatus.PLACED)

    def test_save_twice_does_not_duplicate_lines(self) -> None:
        order = make_order(uuid.uuid4())
        self.repository.save(order)
        order.cancel()

        self.repository.save(order)

        loaded = self.repository.find_by_id(order.id)
        assert loaded is not None
        self.assertEqual(len(loaded.lines), 1)
        self.assertEqual(loaded.status, OrderStatus.CANCELLED)

    def test_count_in_progress_by_customer(self) -> None:
        customer_id = uuid.uuid4()
        in_progress = make_order(customer_id)
        cancelled = make_order(customer_id)
        cancelled.cancel()
        self.repository.save(in_progress)
        self.repository.save(cancelled)
        self.repository.save(make_order(uuid.uuid4()))

        self.assertEqual(self.repository.count_in_progress_by_customer(customer_id), 1)
