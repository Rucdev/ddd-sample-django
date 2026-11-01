import uuid

from django.test import TestCase
from django.urls import reverse

from menu.models import MenuItem
from ordering.domain.entities import Order
from ordering.domain.value_objects import Money, OrderLine
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
        self.assertContains(response, "カフェラテ")
        self.assertContains(response, "¥450")

    def test_order_list_page_shows_menu_item_image(self) -> None:
        self.latte.image = "menu_items/latte.png"
        self.latte.save()

        response = self.client.get(reverse("ordering:order_list"))

        self.assertContains(response, 'src="/media/menu_items/latte.png"')

    def test_preparing_order_shows_progress_per_line(self) -> None:
        order = Order.place(
            customer_id=self.customer.id,
            lines=[
                OrderLine(menu_item_id=uuid.uuid4(), name="カフェラテ", unit_price=Money(450), quantity=1),
                OrderLine(menu_item_id=uuid.uuid4(), name="ホットサンド", unit_price=Money(650), quantity=1),
            ],
        )
        order.start_cooking_line(1)
        order.complete_cooking_line(1)
        order.start_cooking_line(2)
        DjangoOrderRepository().save(order)

        response = self.client.get(reverse("ordering:order_list"))

        self.assertContains(response, "1/2 品できあがり")
        self.assertContains(response, '<span class="line-state line-state--done">できた</span>', html=True)
        self.assertContains(response, '<span class="line-state line-state--cooking">調理中</span>', html=True)

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

        self.assertNotContains(response, f'name="qty_{self.latte.id}"')

    def test_order_list_shows_customer_name_and_member_choices(self) -> None:
        DjangoOrderRepository().save(make_order(self.customer.id))

        response = self.client.get(reverse("ordering:order_list"))

        self.assertContains(response, f'data-customer="{self.customer.id}"')
        self.assertContains(response, '<span class="order-card__customer"', count=1)
        self.assertContains(response, "Alice", count=3)  # 注文カード + 会員選択ダイアログ + JSON

    def test_cancel_order_view(self) -> None:
        order = make_order(self.customer.id)
        DjangoOrderRepository().save(order)

        response = self.client.post(reverse("ordering:cancel_order", args=[order.id]))

        self.assertRedirects(response, reverse("ordering:order_list"))
        cancelled = DjangoOrderRepository().find_by_id(order.id)
        assert cancelled is not None
        self.assertEqual(cancelled.status, "CANCELLED")
