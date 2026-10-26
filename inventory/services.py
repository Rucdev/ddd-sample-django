"""在庫操作の入口。実在庫・予約数を書き換えるのはこのモジュールの関数だけ。

画面(views.py)・API(api.py)・公開 API(public.py)・イベントハンドラはどれもここを呼ぶ。
どの操作も次の 3 つを 1 トランザクションで行う。

1. 条件付き UPDATE で在庫数を書き換える。「注文可能数 >= 数量」を WHERE 句に入れるので、
   同時に注文が来ても売り越さない(読んでから書く間に他の更新が割り込む余地がない)。
2. 実在庫が動いたら在庫ログ(StockMovement)を書く。
3. 注文可能数に合わせて menu の在庫切れフラグを切り替える。
"""

import uuid
from collections.abc import Iterable

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from inventory.exceptions import (
    InsufficientStock,
    KitHasHeldReservations,
    KitInactive,
    KitNotFound,
    ReservationNotFound,
    ReservationNotHeld,
    UnknownMenuItem,
)
from inventory.models import Kit, Reservation, StockMovement
from menu.public import get_menu_item, set_out_of_stock


def register_kit(kit: Kit, initial_quantity: int = 0) -> Kit:
    """キットを登録する。初期在庫は入庫ログとして残す。初期在庫 0 なら商品は即在庫切れになる。"""
    if get_menu_item(kit.menu_item_id) is None:
        raise UnknownMenuItem(kit.menu_item_id)
    with transaction.atomic():
        kit.on_hand = 0
        kit.reserved = 0
        kit.status = Kit.Status.ACTIVE
        kit.save()
        if initial_quantity > 0:
            kit = _change_on_hand(kit, initial_quantity, kind=StockMovement.Kind.RECEIPT, memo="初期在庫")
        _sync_menu(kit)
    return kit


def receive(kit_id: uuid.UUID, quantity: int, memo: str = "") -> Kit:
    """入庫。"""
    with transaction.atomic():
        kit = _get_active_kit(kit_id)
        kit = _change_on_hand(kit, quantity, kind=StockMovement.Kind.RECEIPT, memo=memo)
        _sync_menu(kit)
    return kit


def issue(kit_id: uuid.UUID, quantity: int, memo: str) -> Kit:
    """出庫(廃棄・棚卸差異など)。注文可能数までしか出庫できない(予約分には手を付けない)。"""
    with transaction.atomic():
        kit = _get_active_kit(kit_id)
        kit = _change_on_hand(kit, -quantity, kind=StockMovement.Kind.ISSUE, memo=memo)
        _sync_menu(kit)
    return kit


def reserve(kit_id: uuid.UUID, quantity: int, memo: str = "") -> Reservation:
    """予約の確保。注文可能数までしか確保できない。実在庫は動かないのでログは書かない。"""
    with transaction.atomic():
        kit = _get_active_kit(kit_id)
        updated = Kit.objects.filter(pk=kit.pk, on_hand__gte=F("reserved") + quantity).update(
            reserved=F("reserved") + quantity
        )
        if not updated:
            raise _insufficient(kit.pk, quantity)
        reservation = Reservation.objects.create(kit=kit, quantity=quantity, memo=memo)
        _sync_menu(Kit.objects.get(pk=kit.pk))
    return reservation


def use_reservation(reservation_id: uuid.UUID) -> Reservation:
    """予約の使用。確保した数をすべて実在庫から引く(一部だけの使用はしない)。"""
    with transaction.atomic():
        reservation = _close_reservation(reservation_id, Reservation.Status.USED)
        # 実在庫と予約数を同じだけ減らすので、注文可能数は変わらない。
        _change_on_hand(
            reservation.kit,
            -reservation.quantity,
            reserved_change=-reservation.quantity,
            kind=StockMovement.Kind.RESERVATION_USE,
            memo=reservation.memo,
            reservation=reservation,
        )
    return reservation


def cancel_reservation(reservation_id: uuid.UUID) -> Reservation:
    """予約の取消。確保していた数を注文可能数に戻す。"""
    with transaction.atomic():
        reservation = _close_reservation(reservation_id, Reservation.Status.CANCELLED)
        Kit.objects.filter(pk=reservation.kit_id).update(reserved=F("reserved") - reservation.quantity)
        _sync_menu(Kit.objects.get(pk=reservation.kit_id))
    return reservation


def deactivate_kit(kit_id: uuid.UUID) -> Kit:
    """在庫管理を停止する。以後このキットの商品は在庫チェックの対象外(キット無しと同じ扱い)。"""
    with transaction.atomic():
        kit = _get_kit(kit_id)
        if kit.reservations.filter(status=Reservation.Status.HELD).exists():
            raise KitHasHeldReservations(kit.name)
        kit.status = Kit.Status.INACTIVE
        kit.save(update_fields=["status"])
        _sync_menu(kit)
    return kit


def activate_kit(kit_id: uuid.UUID) -> Kit:
    """在庫管理を再開する。再開した時点の注文可能数で在庫切れを判定し直す。"""
    with transaction.atomic():
        kit = _get_kit(kit_id)
        kit.status = Kit.Status.ACTIVE
        kit.save(update_fields=["status"])
        _sync_menu(kit)
    return kit


def allocate_for_order(order_id: uuid.UUID, lines: Iterable[tuple[uuid.UUID, int]]) -> None:
    """注文の明細 (menu_item_id, 数量) の分だけキットを消費する。

    キットが無い・管理停止中の商品は対象外。1 つでも足りなければ InsufficientStock を投げ、
    それまでに消費した分もロールバックする。
    """
    quantities: dict[uuid.UUID, int] = {}
    for menu_item_id, quantity in lines:
        quantities[menu_item_id] = quantities.get(menu_item_id, 0) + quantity

    with transaction.atomic():
        kits = Kit.objects.filter(menu_item_id__in=quantities, status=Kit.Status.ACTIVE)
        for kit in kits:
            kit = _change_on_hand(
                kit,
                -quantities[kit.menu_item_id],
                kind=StockMovement.Kind.ORDER_ALLOCATION,
                order_id=order_id,
            )
            _sync_menu(kit)


def release_for_order(order_id: uuid.UUID) -> None:
    """注文で消費したキットを戻す。消費の記録(在庫ログ)をもとに戻すので、何度呼ばれても 1 回分だけ戻る。

    消費した後にキットが管理停止になっていても、物としては残っているので実在庫には戻す。
    """
    with transaction.atomic():
        movements = StockMovement.objects.filter(order_id=order_id)
        if movements.filter(kind=StockMovement.Kind.ORDER_RELEASE).exists():
            return
        for allocation in movements.filter(kind=StockMovement.Kind.ORDER_ALLOCATION).select_related("kit"):
            kit = _change_on_hand(
                allocation.kit,
                -allocation.change,
                kind=StockMovement.Kind.ORDER_RELEASE,
                order_id=order_id,
            )
            _sync_menu(kit)


def _get_kit(kit_id: uuid.UUID) -> Kit:
    kit = Kit.objects.filter(pk=kit_id).first()
    if kit is None:
        raise KitNotFound(kit_id)
    return kit


def _get_active_kit(kit_id: uuid.UUID) -> Kit:
    kit = _get_kit(kit_id)
    if not kit.is_active:
        raise KitInactive(kit.name)
    return kit


def _change_on_hand(
    kit: Kit,
    change: int,
    *,
    kind: str,
    reserved_change: int = 0,
    memo: str = "",
    order_id: uuid.UUID | None = None,
    reservation: Reservation | None = None,
) -> Kit:
    """実在庫を change だけ動かして在庫ログを書き、更新後のキットを返す。

    予約分以外から減らす場合(出庫・注文での消費)は、注文可能数が足りることを WHERE 句で確かめる。
    """
    queryset = Kit.objects.filter(pk=kit.pk)
    if change < 0 and reserved_change == 0:
        queryset = queryset.filter(on_hand__gte=F("reserved") - change)
    updated = queryset.update(
        on_hand=F("on_hand") + change, reserved=F("reserved") + reserved_change
    )
    if not updated:
        raise _insufficient(kit.pk, -change)

    kit = Kit.objects.get(pk=kit.pk)
    StockMovement.objects.create(
        kit=kit,
        kind=kind,
        change=change,
        on_hand_after=kit.on_hand,
        memo=memo,
        order_id=order_id,
        reservation=reservation,
    )
    return kit


def _insufficient(kit_id: uuid.UUID, requested: int) -> InsufficientStock:
    kit = Kit.objects.get(pk=kit_id)
    return InsufficientStock(kit.menu_item_id, kit.name, requested, kit.available)


def _close_reservation(reservation_id: uuid.UUID, status: str) -> Reservation:
    # 確保中 → 使用済 / 取消 の遷移も条件付き UPDATE にして、二重に使用・取消されないようにする。
    updated = Reservation.objects.filter(pk=reservation_id, status=Reservation.Status.HELD).update(
        status=status, closed_at=timezone.now()
    )
    reservation = Reservation.objects.select_related("kit").filter(pk=reservation_id).first()
    if reservation is None:
        raise ReservationNotFound(reservation_id)
    if not updated:
        raise ReservationNotHeld(reservation_id, reservation.status)
    return reservation


def _sync_menu(kit: Kit) -> None:
    """注文可能数が 0 なら商品を在庫切れに、1 以上なら在庫切れを外す。管理停止中は常に外す。"""
    set_out_of_stock(kit.menu_item_id, kit.is_active and kit.available == 0)
