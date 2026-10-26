from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory import services
from inventory.models import Kit, StockMovement
from inventory.tests.helpers import create_menu_item, register_kit


class KitAdminTests(TestCase):
    def setUp(self) -> None:
        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(admin)
        self.menu_item = create_menu_item()

    def test_add_kit_records_initial_quantity(self) -> None:
        response = self.client.post(
            reverse("admin:inventory_kit_add"),
            {"menu_item_id": str(self.menu_item.id), "name": "ホットサンドキット", "initial_quantity": 3},
        )

        self.assertEqual(response.status_code, 302)
        kit = Kit.objects.get()
        self.assertEqual(kit.on_hand, 3)
        self.assertEqual(StockMovement.objects.get().kind, "RECEIPT")

    def test_add_kit_for_unknown_menu_item_shows_form_error(self) -> None:
        response = self.client.post(
            reverse("admin:inventory_kit_add"),
            {"menu_item_id": "00000000-0000-0000-0000-000000000000", "name": "x"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Kit.objects.exists())

    def test_editing_name_keeps_on_hand_changed_in_the_meantime(self) -> None:
        kit = register_kit(self.menu_item, initial_quantity=5)
        change_url = reverse("admin:inventory_kit_change", args=[kit.pk])
        self.client.get(change_url)
        services.issue(kit.pk, 2, "廃棄")  # 編集画面を開いている間に在庫が動く

        self.client.post(change_url, {"name": "新しい名前"})

        kit.refresh_from_db()
        self.assertEqual((kit.name, kit.on_hand), ("新しい名前", 3))
