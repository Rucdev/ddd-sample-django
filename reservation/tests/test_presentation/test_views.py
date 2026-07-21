from datetime import date

from django.test import TestCase
from django.urls import reverse

from catalog.models import Title
from members.models import Member
from reservation.infrastructure.models import ReservationModel


class ReservationListViewTests(TestCase):
    def setUp(self) -> None:
        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")

    def test_reservation_list_page_loads(self) -> None:
        response = self.client.get(reverse("reservation:reservation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "予約一覧")

    def test_reserve_title_creates_reservation_and_redirects(self) -> None:
        response = self.client.post(
            reverse("reservation:reserve_title"),
            {"member_id": str(self.member.id), "title_id": str(self.title.id)},
        )

        self.assertRedirects(response, reverse("reservation:reservation_list"))
        self.assertTrue(
            ReservationModel.objects.filter(
                title_id=self.title.id, member_id=self.member.id
            ).exists()
        )

    def test_reserve_title_with_invalid_input_shows_error_message(self) -> None:
        response = self.client.post(
            reverse("reservation:reserve_title"),
            {"member_id": "not-a-uuid", "title_id": str(self.title.id)},
            follow=True,
        )

        page_messages = list(response.context["messages"])
        self.assertTrue(any("入力内容" in str(m) for m in page_messages))

    def test_reserve_title_with_domain_error_shows_error_message(self) -> None:
        ReservationModel.objects.create(
            title_id=self.title.id, member_id=self.member.id, requested_at=date(2026, 1, 1)
        )

        response = self.client.post(
            reverse("reservation:reserve_title"),
            {"member_id": str(self.member.id), "title_id": str(self.title.id)},
            follow=True,
        )

        page_messages = list(response.context["messages"])
        self.assertTrue(any("already has a reservation" in str(m) for m in page_messages))

    def test_cancel_reservation_view(self) -> None:
        ReservationModel.objects.create(
            title_id=self.title.id, member_id=self.member.id, requested_at=date(2026, 1, 1)
        )

        response = self.client.post(
            reverse("reservation:cancel_reservation", args=[self.title.id, self.member.id])
        )

        self.assertRedirects(response, reverse("reservation:reservation_list"))
        self.assertFalse(
            ReservationModel.objects.filter(
                title_id=self.title.id, member_id=self.member.id
            ).exists()
        )
