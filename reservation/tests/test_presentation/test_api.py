from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import Title
from members.models import Member
from reservation.infrastructure.models import ReservationModel


class ReservationAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")

    def test_get_reservations_returns_empty_list_initially(self) -> None:
        response = self.client.get(reverse("reservation:api_reservation_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_post_reservations_creates_reservation(self) -> None:
        response = self.client.post(
            reverse("reservation:api_reservation_list"),
            {"member_id": str(self.member.id), "title_id": str(self.title.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["member_id"], str(self.member.id))
        self.assertEqual(response.data["position"], 1)

    def test_post_reservations_with_invalid_input_returns_400(self) -> None:
        response = self.client.post(
            reverse("reservation:api_reservation_list"), {"member_id": "nope"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_reservations_domain_conflict_returns_409(self) -> None:
        ReservationModel.objects.create(
            title_id=self.title.id, member_id=self.member.id, requested_at=date(2026, 1, 1)
        )

        response = self.client.post(
            reverse("reservation:api_reservation_list"),
            {"member_id": str(self.member.id), "title_id": str(self.title.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_reservation_cancels_it(self) -> None:
        ReservationModel.objects.create(
            title_id=self.title.id, member_id=self.member.id, requested_at=date(2026, 1, 1)
        )

        response = self.client.delete(
            reverse("reservation:api_reservation_cancel", args=[self.title.id, self.member.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            ReservationModel.objects.filter(
                title_id=self.title.id, member_id=self.member.id
            ).exists()
        )

    def test_delete_unknown_reservation_returns_404(self) -> None:
        response = self.client.delete(
            reverse(
                "reservation:api_reservation_cancel", args=[self.title.id, self.member.id]
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
