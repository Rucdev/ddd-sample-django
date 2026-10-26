import uuid

from django.test import TestCase

from inventory import services
from inventory.exceptions import (
    InsufficientStock,
    KitHasHeldReservations,
    KitInactive,
    ReservationNotHeld,
    UnknownMenuItem,
)
from inventory.models import Kit, Reservation, StockMovement
from inventory.tests.helpers import create_menu_item, register_kit


class _KitTestCase(TestCase):
    def setUp(self) -> None:
        self.menu_item = create_menu_item()
        self.kit = register_kit(self.menu_item, initial_quantity=5)

    def _kit(self) -> Kit:
        return Kit.objects.get(pk=self.kit.pk)

    def _out_of_stock(self) -> bool:
        self.menu_item.refresh_from_db()
        return self.menu_item.out_of_stock

    def _assert_on_hand_matches_log(self) -> None:
        # 実在庫 = 在庫ログの増減量の合計(キットは 0 から始まる)
        total = sum(m.change for m in StockMovement.objects.filter(kit=self.kit))
        self.assertEqual(self._kit().on_hand, total)


class RegisterKitTests(_KitTestCase):
    def test_initial_quantity_is_recorded_as_receipt(self) -> None:
        movement = StockMovement.objects.get(kit=self.kit)

        self.assertEqual((movement.kind, movement.change, movement.on_hand_after), ("RECEIPT", 5, 5))
        self.assertFalse(self._out_of_stock())

    def test_kit_with_zero_initial_quantity_makes_menu_item_out_of_stock(self) -> None:
        other = create_menu_item("スコーン", 300)

        register_kit(other, initial_quantity=0)

        other.refresh_from_db()
        self.assertTrue(other.out_of_stock)

    def test_unknown_menu_item_is_rejected(self) -> None:
        with self.assertRaises(UnknownMenuItem):
            services.register_kit(Kit(menu_item_id=uuid.uuid4(), name="謎のキット"))


class ReceiveAndIssueTests(_KitTestCase):
    def test_receive_increases_on_hand_and_logs(self) -> None:
        kit = services.receive(self.kit.pk, 3, "入荷")

        self.assertEqual(kit.on_hand, 8)
        self._assert_on_hand_matches_log()

    def test_receive_clears_out_of_stock(self) -> None:
        services.issue(self.kit.pk, 5, "廃棄")
        self.assertTrue(self._out_of_stock())

        services.receive(self.kit.pk, 1)

        self.assertFalse(self._out_of_stock())

    def test_issue_cannot_touch_reserved_kits(self) -> None:
        services.reserve(self.kit.pk, 3)

        with self.assertRaises(InsufficientStock) as ctx:
            services.issue(self.kit.pk, 3, "廃棄")

        self.assertEqual(ctx.exception.available, 2)
        self.assertEqual(self._kit().on_hand, 5)

    def test_inactive_kit_cannot_be_received(self) -> None:
        services.deactivate_kit(self.kit.pk)

        with self.assertRaises(KitInactive):
            services.receive(self.kit.pk, 1)


class ReservationTests(_KitTestCase):
    def test_reserve_reduces_available_without_touching_on_hand(self) -> None:
        services.reserve(self.kit.pk, 2, "団体客")

        kit = self._kit()
        self.assertEqual((kit.on_hand, kit.reserved, kit.available), (5, 2, 3))
        self.assertEqual(StockMovement.objects.filter(kit=self.kit).count(), 1)  # 初期在庫の分だけ

    def test_cannot_reserve_more_than_available(self) -> None:
        with self.assertRaises(InsufficientStock):
            services.reserve(self.kit.pk, 6)

    def test_reserving_everything_makes_menu_item_out_of_stock(self) -> None:
        services.reserve(self.kit.pk, 5)

        self.assertTrue(self._out_of_stock())

    def test_use_consumes_on_hand_and_logs(self) -> None:
        reservation = services.reserve(self.kit.pk, 2)

        services.use_reservation(reservation.pk)

        kit = self._kit()
        self.assertEqual((kit.on_hand, kit.reserved), (3, 0))
        movement = StockMovement.objects.get(kind="RESERVATION_USE")
        self.assertEqual((movement.change, movement.reservation_id), (-2, reservation.pk))
        self._assert_on_hand_matches_log()

    def test_cancel_returns_quantity_to_available(self) -> None:
        reservation = services.reserve(self.kit.pk, 5)

        services.cancel_reservation(reservation.pk)

        self.assertEqual(self._kit().available, 5)
        self.assertFalse(self._out_of_stock())

    def test_closed_reservation_cannot_be_used_again(self) -> None:
        reservation = services.reserve(self.kit.pk, 2)
        services.use_reservation(reservation.pk)

        with self.assertRaises(ReservationNotHeld):
            services.use_reservation(reservation.pk)
        with self.assertRaises(ReservationNotHeld):
            services.cancel_reservation(reservation.pk)
        self.assertEqual(self._kit().on_hand, 3)


class ActivationTests(_KitTestCase):
    def test_deactivate_clears_out_of_stock(self) -> None:
        services.issue(self.kit.pk, 5, "廃棄")

        services.deactivate_kit(self.kit.pk)

        self.assertFalse(self._out_of_stock())

    def test_cannot_deactivate_with_held_reservations(self) -> None:
        services.reserve(self.kit.pk, 1)

        with self.assertRaises(KitHasHeldReservations):
            services.deactivate_kit(self.kit.pk)

    def test_activate_rechecks_out_of_stock(self) -> None:
        services.issue(self.kit.pk, 5, "廃棄")
        services.deactivate_kit(self.kit.pk)

        services.activate_kit(self.kit.pk)

        self.assertTrue(self._out_of_stock())


class OrderAllocationTests(_KitTestCase):
    def test_allocate_sums_lines_of_same_menu_item(self) -> None:
        order_id = uuid.uuid4()

        services.allocate_for_order(order_id, [(self.menu_item.id, 2), (self.menu_item.id, 1)])

        self.assertEqual(self._kit().on_hand, 2)
        movement = StockMovement.objects.get(kind="ORDER_ALLOCATION")
        self.assertEqual((movement.change, movement.order_id), (-3, order_id))

    def test_allocate_ignores_items_without_kit_or_inactive_kit(self) -> None:
        no_kit = create_menu_item("ドリップコーヒー", 350)
        services.deactivate_kit(self.kit.pk)

        services.allocate_for_order(uuid.uuid4(), [(no_kit.id, 10), (self.menu_item.id, 10)])

        self.assertEqual(self._kit().on_hand, 5)

    def test_allocate_fails_atomically_when_any_kit_is_short(self) -> None:
        other = create_menu_item("スコーン", 300)
        other_kit = register_kit(other, initial_quantity=1)

        with self.assertRaises(InsufficientStock) as ctx:
            services.allocate_for_order(uuid.uuid4(), [(self.menu_item.id, 2), (other.id, 2)])

        self.assertEqual(ctx.exception.menu_item_id, other.id)
        self.assertEqual(self._kit().on_hand, 5)
        self.assertEqual(Kit.objects.get(pk=other_kit.pk).on_hand, 1)

    def test_allocate_does_not_use_reserved_kits(self) -> None:
        services.reserve(self.kit.pk, 4)

        with self.assertRaises(InsufficientStock):
            services.allocate_for_order(uuid.uuid4(), [(self.menu_item.id, 2)])

    def test_release_restores_once(self) -> None:
        order_id = uuid.uuid4()
        services.allocate_for_order(order_id, [(self.menu_item.id, 5)])
        self.assertTrue(self._out_of_stock())

        services.release_for_order(order_id)
        services.release_for_order(order_id)

        self.assertEqual(self._kit().on_hand, 5)
        self.assertFalse(self._out_of_stock())
        self._assert_on_hand_matches_log()

    def test_reservation_status_is_untouched_by_orders(self) -> None:
        reservation = services.reserve(self.kit.pk, 1)

        services.allocate_for_order(uuid.uuid4(), [(self.menu_item.id, 4)])

        self.assertEqual(Reservation.objects.get(pk=reservation.pk).status, "HELD")
