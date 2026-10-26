import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from menu import public
from menu.models import Category, MenuItem


class MenuItemModelTests(TestCase):
    def setUp(self) -> None:
        self.category = Category.objects.create(name="ドリンク")

    def test_name_must_be_unique(self) -> None:
        MenuItem.objects.create(category=self.category, name="カフェラテ", price=450)

        with self.assertRaises(IntegrityError), transaction.atomic():
            MenuItem.objects.create(category=self.category, name="カフェラテ", price=500)

    def test_default_status_is_on_sale(self) -> None:
        item = MenuItem.objects.create(category=self.category, name="カフェラテ", price=450)

        self.assertEqual(item.status, MenuItem.Status.ON_SALE)


class PublicApiTests(TestCase):
    def setUp(self) -> None:
        category = Category.objects.create(name="ドリンク")
        self.latte = MenuItem.objects.create(category=category, name="カフェラテ", price=450)
        self.mocha = MenuItem.objects.create(
            category=category, name="カフェモカ", price=500, status=MenuItem.Status.SOLD_OUT
        )

    def test_get_menu_item_returns_dto(self) -> None:
        dto = public.get_menu_item(self.latte.id)

        assert dto is not None
        self.assertEqual(dto.name, "カフェラテ")
        self.assertEqual(dto.price, 450)
        self.assertEqual(dto.category_name, "ドリンク")
        self.assertTrue(dto.is_available)

    def test_get_menu_item_reflects_sold_out(self) -> None:
        dto = public.get_menu_item(self.mocha.id)

        assert dto is not None
        self.assertFalse(dto.is_available)

    def test_get_menu_item_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_menu_item(uuid.uuid4()))

    def test_list_available_menu_items_excludes_sold_out(self) -> None:
        names = [item.name for item in public.list_available_menu_items()]

        self.assertEqual(names, ["カフェラテ"])

    def test_out_of_stock_item_is_not_available(self) -> None:
        public.set_out_of_stock(self.latte.id, True)

        dto = public.get_menu_item(self.latte.id)
        assert dto is not None
        self.assertFalse(dto.is_available)
        self.assertEqual(public.list_available_menu_items(), [])

    def test_out_of_stock_does_not_change_manual_status(self) -> None:
        public.set_out_of_stock(self.mocha.id, True)
        public.set_out_of_stock(self.mocha.id, False)

        self.mocha.refresh_from_db()
        self.assertEqual(self.mocha.status, MenuItem.Status.SOLD_OUT)
