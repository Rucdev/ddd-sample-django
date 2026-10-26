from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from inventory import services
from inventory.models import Kit, Reservation, StockMovement
from inventory.tests.helpers import create_menu_item, register_kit


class InventoryScreenTests(TestCase):
    def setUp(self) -> None:
        self.kit = register_kit(create_menu_item(), initial_quantity=5)

    def _messages(self, response) -> list[str]:
        return [str(m) for m in response.context["messages"]]

    def test_list_page_shows_counts(self) -> None:
        services.reserve(self.kit.pk, 2, "団体客")

        response = self.client.get(reverse("inventory:kit_list"))

        self.assertContains(response, "ホットサンドキット")
        self.assertContains(response, "団体客")
        self.assertEqual(response.context["kits"][0].available, 3)

    def test_receive_view(self) -> None:
        response = self.client.post(
            reverse("inventory:receive", args=[self.kit.pk]), {"quantity": 3, "memo": "入荷"}
        )

        self.assertRedirects(response, reverse("inventory:kit_list"))
        self.assertEqual(Kit.objects.get(pk=self.kit.pk).on_hand, 8)

    def test_issue_requires_reason(self) -> None:
        response = self.client.post(
            reverse("inventory:issue", args=[self.kit.pk]), {"quantity": 1}, follow=True
        )

        self.assertIn("入力内容を確認してください。", self._messages(response))
        self.assertEqual(Kit.objects.get(pk=self.kit.pk).on_hand, 5)

    def test_issue_beyond_available_shows_error(self) -> None:
        response = self.client.post(
            reverse("inventory:issue", args=[self.kit.pk]),
            {"quantity": 6, "memo": "廃棄"},
            follow=True,
        )

        self.assertTrue(any("available" in m for m in self._messages(response)))

    def test_reserve_then_use(self) -> None:
        self.client.post(reverse("inventory:reserve", args=[self.kit.pk]), {"quantity": 2})
        reservation = Reservation.objects.get()

        self.client.post(reverse("inventory:use_reservation", args=[reservation.pk]))

        self.assertEqual(Kit.objects.get(pk=self.kit.pk).on_hand, 3)

    def test_deactivate_and_activate(self) -> None:
        self.client.post(reverse("inventory:deactivate_kit", args=[self.kit.pk]))
        self.assertEqual(Kit.objects.get(pk=self.kit.pk).status, "INACTIVE")

        self.client.post(reverse("inventory:activate_kit", args=[self.kit.pk]))
        self.assertEqual(Kit.objects.get(pk=self.kit.pk).status, "ACTIVE")


class InventoryAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.menu_item = create_menu_item()

    def _create_kit(self, initial_quantity: int = 5) -> dict:
        response = self.client.post(
            reverse("inventory:api-kit-list"),
            {"menu_item_id": str(self.menu_item.id), "name": "ホットサンドキット",
             "initial_quantity": initial_quantity},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        return response.json()

    def test_create_kit_with_initial_quantity(self) -> None:
        kit = self._create_kit(4)

        self.assertEqual((kit["on_hand"], kit["available"], kit["status"]), (4, 4, "ACTIVE"))
        self.assertEqual(StockMovement.objects.get().kind, "RECEIPT")

    def test_create_kit_for_unknown_menu_item_returns_400(self) -> None:
        response = self.client.post(
            reverse("inventory:api-kit-list"),
            {"menu_item_id": "00000000-0000-0000-0000-000000000000", "name": "x"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_on_hand_cannot_be_written_directly(self) -> None:
        kit = self._create_kit(5)

        response = self.client.patch(
            reverse("inventory:api-kit-detail", args=[kit["id"]]),
            {"name": "新しい名前", "on_hand": 999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((response.json()["name"], response.json()["on_hand"]), ("新しい名前", 5))

    def test_menu_item_cannot_be_changed_after_creation(self) -> None:
        kit = self._create_kit()
        other = create_menu_item("スコーン", 300)

        response = self.client.patch(
            reverse("inventory:api-kit-detail", args=[kit["id"]]),
            {"menu_item_id": str(other.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kits_cannot_be_deleted(self) -> None:
        kit = self._create_kit()

        response = self.client.delete(reverse("inventory:api-kit-detail", args=[kit["id"]]))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_receive_and_issue_actions(self) -> None:
        kit = self._create_kit(5)

        received = self.client.post(
            reverse("inventory:api-kit-receive", args=[kit["id"]]), {"quantity": 2}, format="json"
        )
        issued = self.client.post(
            reverse("inventory:api-kit-issue", args=[kit["id"]]),
            {"quantity": 3, "memo": "廃棄"},
            format="json",
        )

        self.assertEqual(received.json()["on_hand"], 7)
        self.assertEqual(issued.json()["on_hand"], 4)

    def test_issue_beyond_available_returns_409(self) -> None:
        kit = self._create_kit(1)

        response = self.client.post(
            reverse("inventory:api-kit-issue", args=[kit["id"]]),
            {"quantity": 2, "memo": "廃棄"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_unknown_kit_returns_404(self) -> None:
        response = self.client.post(
            reverse("inventory:api-kit-receive", args=["00000000-0000-0000-0000-000000000000"]),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reservation_lifecycle(self) -> None:
        kit = self._create_kit(5)

        created = self.client.post(
            reverse("inventory:api-reservation-list"),
            {"kit": kit["id"], "quantity": 2, "memo": "団体客"},
            format="json",
        )
        reservation_id = created.json()["id"]
        cancelled = self.client.post(
            reverse("inventory:api-reservation-cancel", args=[reservation_id])
        )
        cancelled_again = self.client.post(
            reverse("inventory:api-reservation-cancel", args=[reservation_id])
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(cancelled.json()["status"], "CANCELLED")
        self.assertEqual(cancelled_again.status_code, status.HTTP_409_CONFLICT)

    def test_reservation_beyond_available_returns_409(self) -> None:
        kit = self._create_kit(1)

        response = self.client.post(
            reverse("inventory:api-reservation-list"),
            {"kit": kit["id"], "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_movements_can_be_filtered_by_kind(self) -> None:
        kit = self._create_kit(5)
        self.client.post(reverse("inventory:api-kit-receive", args=[kit["id"]]), {"quantity": 1})
        self.client.post(
            reverse("inventory:api-kit-issue", args=[kit["id"]]), {"quantity": 1, "memo": "廃棄"}
        )

        response = self.client.get(reverse("inventory:api-movement-list"), {"kind": "ISSUE"})

        self.assertEqual([m["change"] for m in response.json()], [-1])
