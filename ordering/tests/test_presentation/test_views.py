from django.test import TestCase
from django.urls import reverse

from menu.models import MenuItem
from ordering.infrastructure.models import OrderModel
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import create_customer, create_menu_item, make_order


class OrderViewTests(TestCase):
    def setUp(self) -> None:
        self.customer = create_customer()
        self.latte = create_menu_item("カフェラテ", 450)

    def test_order_list_page_shows_available_menu_items(self) -> None:
        response = self.client.get(reverse("ordering:order_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注文一覧")
        self.assertContains(response, "カフェラテ(450円)")

    def test_place_order_creates_order_and_redirects(self) -> None:
        response = self.client.post(
            reverse("ordering:place_order"),
            {"customer_id": str(self.customer.id), f"qty_{self.latte.id}": "2"},
        )

        self.assertRedirects(response, reverse("ordering:order_list"))
        self.assertEqual(OrderModel.objects.count(), 1)

    def test_place_order_without_any_item_shows_domain_error(self) -> None:
        response = self.client.post(
            reverse("ordering:place_order"),
            {"customer_id": str(self.customer.id), f"qty_{self.latte.id}": "0"},
            follow=True,
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("at least one line" in m for m in page_messages))

    def test_place_order_with_invalid_input_shows_error_message(self) -> None:
        response = self.client.post(
            reverse("ordering:place_order"), {"customer_id": "not-a-uuid"}, follow=True
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("入力内容" in m for m in page_messages))

    def test_sold_out_items_are_not_on_the_form(self) -> None:
        self.latte.status = MenuItem.Status.SOLD_OUT
        self.latte.save()

        response = self.client.get(reverse("ordering:order_list"))

        self.assertNotContains(response, "カフェラテ(450円)")

    def test_cancel_order_view(self) -> None:
        order = make_order(self.customer.id)
        DjangoOrderRepository().save(order)

        response = self.client.post(reverse("ordering:cancel_order", args=[order.id]))

        self.assertRedirects(response, reverse("ordering:order_list"))
        cancelled = DjangoOrderRepository().find_by_id(order.id)
        assert cancelled is not None
        self.assertEqual(cancelled.status, "CANCELLED")
