import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from menu.models import MenuItem
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import create_customer, create_menu_item, make_order


class OrderAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = create_customer()
        self.latte = create_menu_item("カフェラテ", 450)

    def _post_order(self, quantity: int = 1):
        return self.client.post(
            reverse("ordering:api_order_list"),
            {
                "customer_id": str(self.customer.id),
                "lines": [{"menu_item_id": str(self.latte.id), "quantity": quantity}],
            },
            format="json",
        )

    def test_get_orders_returns_empty_list_initially(self) -> None:
        response = self.client.get(reverse("ordering:api_order_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_post_orders_creates_order(self) -> None:
        response = self._post_order(quantity=2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], "PLACED")
        self.assertEqual(response.json()["total"], 900)
        self.assertEqual(response.json()["lines"][0]["name"], "カフェラテ")

    def test_post_orders_with_invalid_input_returns_400(self) -> None:
        response = self.client.post(
            reverse("ordering:api_order_list"), {"customer_id": "nope"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_orders_domain_conflict_returns_409(self) -> None:
        self.latte.status = MenuItem.Status.SOLD_OUT
        self.latte.save()

        response = self._post_order()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_order_api(self) -> None:
        order = make_order(self.customer.id)
        DjangoOrderRepository().save(order)

        response = self.client.post(reverse("ordering:api_cancel_order", args=[order.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "CANCELLED")

    def test_pick_up_before_ready_returns_409(self) -> None:
        order = make_order(self.customer.id)
        DjangoOrderRepository().save(order)

        response = self.client.post(reverse("ordering:api_pick_up_order", args=[order.id]))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_unknown_order_returns_404(self) -> None:
        response = self.client.post(reverse("ordering:api_cancel_order", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
