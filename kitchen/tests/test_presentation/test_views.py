import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from kitchen.domain.entities import Ticket
from kitchen.domain.value_objects import TicketItem
from kitchen.infrastructure.repositories import DjangoTicketRepository
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.tests.test_application.factories import make_order


def _open_ticket(name: str) -> Ticket:
    # チケットの調理開始は ordering 側の注文を「調理中」にするので、対応する注文も用意する。
    order = make_order(uuid.uuid4())
    DjangoOrderRepository().save(order)
    ticket = Ticket.open(order_id=order.id, items=[TicketItem(name=name, quantity=2)])
    DjangoTicketRepository().save(ticket)
    return ticket


class _TicketFixtureMixin:
    def setUp(self) -> None:
        self.ticket = _open_ticket("カフェラテ")


class TicketViewTests(_TicketFixtureMixin, TestCase):
    def test_ticket_list_page_shows_open_tickets(self) -> None:
        response = self.client.get(reverse("kitchen:ticket_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "カフェラテ × 2")

    def test_start_cooking_view(self) -> None:
        response = self.client.post(reverse("kitchen:start_cooking", args=[self.ticket.id]))

        self.assertRedirects(response, reverse("kitchen:ticket_list"))
        ticket = DjangoTicketRepository().find_by_id(self.ticket.id)
        assert ticket is not None
        self.assertEqual(ticket.status, "COOKING")

    def test_complete_before_start_shows_error_message(self) -> None:
        response = self.client.post(
            reverse("kitchen:complete_cooking", args=[self.ticket.id]), follow=True
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("cannot be completed" in m for m in page_messages))


class TicketAPITests(_TicketFixtureMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()

    def test_get_tickets(self) -> None:
        response = self.client.get(reverse("kitchen:api_ticket_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["items"], [{"name": "カフェラテ", "quantity": 2}])

    def test_filter_tickets_by_status(self) -> None:
        cooking = _open_ticket("カプチーノ")
        self.client.post(reverse("kitchen:api_start_cooking", args=[cooking.id]))

        response = self.client.get(reverse("kitchen:api_ticket_list"), {"status": "COOKING"})

        self.assertEqual([t["id"] for t in response.json()], [str(cooking.id)])

    def test_filter_tickets_by_multiple_statuses(self) -> None:
        cooking = _open_ticket("カプチーノ")
        self.client.post(reverse("kitchen:api_start_cooking", args=[cooking.id]))

        response = self.client.get(
            reverse("kitchen:api_ticket_list"), {"status": ["QUEUED", "COOKING"]}
        )

        self.assertEqual(len(response.json()), 2)

    def test_filter_tickets_by_order_id(self) -> None:
        _open_ticket("カプチーノ")

        response = self.client.get(
            reverse("kitchen:api_ticket_list"), {"order_id": str(self.ticket.order_id)}
        )

        self.assertEqual([t["id"] for t in response.json()], [str(self.ticket.id)])

    def test_unknown_status_returns_400(self) -> None:
        response = self.client.get(reverse("kitchen:api_ticket_list"), {"status": "BURNT"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tickets_are_oldest_first_and_can_be_reversed(self) -> None:
        newer = _open_ticket("カプチーノ")

        default = self.client.get(reverse("kitchen:api_ticket_list"))
        reversed_ = self.client.get(reverse("kitchen:api_ticket_list"), {"ordering": "-created_at"})

        self.assertEqual([t["id"] for t in default.json()], [str(self.ticket.id), str(newer.id)])
        self.assertEqual([t["id"] for t in reversed_.json()], [str(newer.id), str(self.ticket.id)])

    def test_start_then_complete(self) -> None:
        start = self.client.post(reverse("kitchen:api_start_cooking", args=[self.ticket.id]))
        complete = self.client.post(reverse("kitchen:api_complete_cooking", args=[self.ticket.id]))

        self.assertEqual(start.json()["status"], "COOKING")
        self.assertEqual(complete.json()["status"], "DONE")

    def test_complete_before_start_returns_409(self) -> None:
        response = self.client.post(reverse("kitchen:api_complete_cooking", args=[self.ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_unknown_ticket_returns_404(self) -> None:
        response = self.client.post(reverse("kitchen:api_start_cooking", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
