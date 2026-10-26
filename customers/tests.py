import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from customers import public
from customers.event_handlers import handle_order_picked_up
from customers.models import Customer
from ordering.domain.events import OrderPickedUp


class CustomerModelTests(TestCase):
    def test_email_must_be_unique(self) -> None:
        Customer.objects.create(name="Alice", email="alice@example.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Customer.objects.create(name="Alice Duplicate", email="alice@example.com")

    def test_defaults(self) -> None:
        customer = Customer.objects.create(name="Alice", email="alice@example.com")

        self.assertEqual(customer.status, Customer.Status.ACTIVE)
        self.assertEqual(customer.rank, Customer.Rank.REGULAR)
        self.assertEqual(customer.points, 0)


class PublicApiTests(TestCase):
    def setUp(self) -> None:
        self.customer = Customer.objects.create(name="Alice", email="alice@example.com")

    def test_get_customer_returns_dto(self) -> None:
        dto = public.get_customer(self.customer.id)

        assert dto is not None
        self.assertEqual(dto.name, "Alice")
        self.assertTrue(dto.is_active)
        self.assertEqual(dto.rank, "REGULAR")

    def test_get_customer_reflects_suspension(self) -> None:
        self.customer.status = Customer.Status.SUSPENDED
        self.customer.save()

        dto = public.get_customer(self.customer.id)

        assert dto is not None
        self.assertFalse(dto.is_active)

    def test_get_customer_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_customer(uuid.uuid4()))

    def test_add_points(self) -> None:
        public.add_points(self.customer.id, 5)
        public.add_points(self.customer.id, 3)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 8)


class OrderPickedUpHandlerTests(TestCase):
    def setUp(self) -> None:
        self.customer = Customer.objects.create(name="Alice", email="alice@example.com")

    def _pick_up(self, total: int) -> None:
        handle_order_picked_up(
            OrderPickedUp(order_id=uuid.uuid4(), customer_id=self.customer.id, total=total)
        )

    def test_one_point_per_100_yen_rounded_down(self) -> None:
        self._pick_up(1299)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 12)

    def test_under_100_yen_gives_no_points(self) -> None:
        self._pick_up(99)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 0)
