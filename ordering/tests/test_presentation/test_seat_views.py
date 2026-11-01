import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ordering.application.use_cases.manage_bill import OpenBillUseCase, SettleBillUseCase
from ordering.domain.entities import Order
from ordering.domain.value_objects import Money, OrderLine
from ordering.infrastructure.models import OrderModel
from ordering.infrastructure.repositories import DjangoBillRepository, DjangoOrderRepository
from ordering.tests.test_application.factories import create_menu_item


def _open_bill(seat_code: str = "T1") -> uuid.UUID:
    seat_id = uuid.uuid4()
    OpenBillUseCase(DjangoBillRepository()).execute(seat_id, seat_code)
    return seat_id


def _ready_order_at(seat_id: uuid.UUID, *, price: int = 450) -> Order:
    bill = DjangoBillRepository().find_open_by_seat(seat_id)
    assert bill is not None
    order = Order.place_at_seat(
        bill=bill,
        lines=[OrderLine(menu_item_id=uuid.uuid4(), name="カフェラテ", unit_price=Money(price), quantity=1)],
    )
    order.start_cooking_line(1)
    order.complete_cooking_line(1)
    DjangoOrderRepository().save(order)
    return order


class SeatOrderViewTests(TestCase):
    def setUp(self) -> None:
        self.latte = create_menu_item("カフェラテ", 450)
        self.seat_id = _open_bill("T1")

    def test_seat_page_shows_menu_without_member_login(self) -> None:
        response = self.client.get(reverse("ordering:seat_order", args=[self.seat_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "お席 <strong>T1</strong>", html=True)
        self.assertContains(response, "カフェラテ")
        self.assertNotContains(response, "会員を選ぶ")

    def test_seat_page_without_open_bill_does_not_take_orders(self) -> None:
        response = self.client.get(reverse("ordering:seat_order", args=[uuid.uuid4()]))

        self.assertContains(response, "ご注文を受け付けていません")
        self.assertNotContains(response, "注文する")

    def test_place_seat_order_and_see_it_in_the_bill(self) -> None:
        response = self.client.post(
            reverse("ordering:place_seat_order", args=[self.seat_id]),
            {f"qty_{self.latte.id}": "2"},
            follow=True,
        )

        self.assertRedirects(response, reverse("ordering:seat_order", args=[self.seat_id]))
        self.assertEqual(OrderModel.objects.get().order_type, "DINE_IN")
        self.assertContains(response, "お会計 <strong>¥900</strong>", html=True)
        self.assertContains(response, "受付済")

    def test_place_seat_order_on_closed_seat_shows_message(self) -> None:
        SettleBillUseCase(DjangoBillRepository()).execute(self.seat_id)

        response = self.client.post(
            reverse("ordering:place_seat_order", args=[self.seat_id]),
            {f"qty_{self.latte.id}": "1"},
            follow=True,
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("ご注文を受け付けていません" in m for m in page_messages))
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_cancel_seat_order(self) -> None:
        self.client.post(
            reverse("ordering:place_seat_order", args=[self.seat_id]), {f"qty_{self.latte.id}": "1"}
        )
        order = OrderModel.objects.get()

        self.client.post(reverse("ordering:cancel_seat_order", args=[self.seat_id, order.id]))

        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")

    def test_ready_order_is_shown_as_waiting_to_be_served(self) -> None:
        _ready_order_at(self.seat_id)

        response = self.client.get(reverse("ordering:seat_order", args=[self.seat_id]))

        self.assertContains(response, "提供待ち")

    def test_takeout_order_list_does_not_show_dine_in_orders(self) -> None:
        _ready_order_at(self.seat_id)

        response = self.client.get(reverse("ordering:order_list"))

        self.assertEqual(response.context["rows"], [])


class FloorViewTests(TestCase):
    def setUp(self) -> None:
        self.seat_id = _open_bill("T1")

    def test_floor_lists_open_bills_with_waiting_orders(self) -> None:
        _ready_order_at(self.seat_id, price=500)

        response = self.client.get(reverse("ordering:floor"))

        self.assertContains(response, '<span class="bill-card__seat">T1</span>', html=True)
        self.assertContains(response, "提供完了")
        self.assertContains(response, "<strong>¥500</strong>", html=True)

    def test_serve_order_from_floor(self) -> None:
        order = _ready_order_at(self.seat_id)

        response = self.client.post(reverse("ordering:serve_order", args=[order.id]), follow=True)

        self.assertRedirects(response, reverse("ordering:floor"))
        self.assertEqual(OrderModel.objects.get(id=order.id).status, "SERVED")
        self.assertContains(response, "提供済")

    def test_paid_bill_moves_to_recent_bills(self) -> None:
        _ready_order_at(self.seat_id, price=700)
        SettleBillUseCase(DjangoBillRepository()).execute(self.seat_id)

        response = self.client.get(reverse("ordering:floor"))

        self.assertEqual(response.context["bills"], [])
        self.assertEqual([b.amount_due for b in response.context["paid_bills"]], [700])


class SeatOrderAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.latte = create_menu_item("カフェラテ", 450)
        self.seat_id = _open_bill("T1")

    def _post(self, seat_id: uuid.UUID):
        return self.client.post(
            reverse("ordering:api_place_seat_order", args=[seat_id]),
            {"lines": [{"menu_item_id": str(self.latte.id), "quantity": 1}]},
            format="json",
        )

    def test_place_seat_order(self) -> None:
        response = self._post(self.seat_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["order_type"], "DINE_IN")
        self.assertIsNone(body["customer_id"])

    def test_place_seat_order_on_unused_seat_is_conflict(self) -> None:
        self.assertEqual(self._post(uuid.uuid4()).status_code, status.HTTP_409_CONFLICT)

    def test_seat_bill(self) -> None:
        self._post(self.seat_id)

        response = self.client.get(reverse("ordering:api_seat_bill", args=[self.seat_id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["amount_due"], 450)
        self.assertEqual(len(response.json()["orders"]), 1)

    def test_seat_bill_of_unused_seat_is_not_found(self) -> None:
        response = self.client.get(reverse("ordering:api_seat_bill", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_serve_order(self) -> None:
        order = _ready_order_at(self.seat_id)

        response = self.client.post(reverse("ordering:api_serve_order", args=[order.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "SERVED")

    def test_serving_twice_is_conflict(self) -> None:
        url = reverse("ordering:api_serve_order", args=[_ready_order_at(self.seat_id).id])
        self.client.post(url)

        self.assertEqual(self.client.post(url).status_code, status.HTTP_409_CONFLICT)
