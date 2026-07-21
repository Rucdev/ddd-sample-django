import uuid
from datetime import date, timedelta

from reservation.domain.events import HoldExpired, HoldReady
from reservation.domain.exceptions import DuplicateReservation, NotReserved
from reservation.domain.value_objects import HOLD_PERIOD_DAYS, Hold, Reservation
from shared.domain.entity import Entity


class ReservationQueue(Entity):
    """予約待ち行列。集約ルート。書誌(title_id)単位で 1 つ持つ。

    予約は書誌単位で行い、どの蔵書(個体)が割り当たるかは返却時に決まる
    (reservation/CONTEXT.md 参照)。そのため集約は「まだ順番待ちの予約」(FIFO)と
    「すでに割り当てられた取置」の両方を保持する。
    """

    def __init__(
        self,
        *,
        title_id: uuid.UUID,
        reservations: list[Reservation] | None = None,
        holds: list[Hold] | None = None,
    ) -> None:
        super().__init__()
        self.id = title_id
        self.title_id = title_id
        self.reservations = list(reservations) if reservations else []
        self.holds = list(holds) if holds else []

    def add_reservation(self, *, member_id: uuid.UUID, today: date) -> None:
        """予約を申し込む。同一会員の重複予約(すでに待機中、またはすでに取置がある)は不可。"""
        if self._is_waiting_or_holding(member_id):
            raise DuplicateReservation(self.title_id, member_id)
        self.reservations.append(Reservation(member_id=member_id, requested_at=today))

    def cancel(self, member_id: uuid.UUID) -> None:
        """待機中の予約を取り消す。取置(Hold)に進んだ後の取消はここでは扱わない
        (このサンプルでは「取置が成立したら取消不可」という単純化をしている)。
        """
        for reservation in self.reservations:
            if reservation.member_id == member_id:
                self.reservations.remove(reservation)
                return
        raise NotReserved(self.title_id, member_id)

    def assign_hold(self, *, copy_id: uuid.UUID, today: date) -> Hold | None:
        """返却された蔵書(copy_id)を、待ち行列の先頭の会員のために取置に変える。

        誰も待っていなければ何もしない(None を返す)。lending 側からは
        「この蔵書は誰にも取置されていない = 普通に貸せる」として扱われる。
        """
        if not self.reservations:
            return None
        next_reservation = self.reservations.pop(0)
        hold = Hold(
            copy_id=copy_id,
            member_id=next_reservation.member_id,
            expires_at=today + timedelta(days=HOLD_PERIOD_DAYS),
        )
        self.holds.append(hold)
        self.record_event(
            HoldReady(title_id=self.title_id, copy_id=copy_id, member_id=hold.member_id)
        )
        return hold

    def expire_holds(self, today: date) -> None:
        """期限切れの取置を解除する。次の予約者が待っていれば、同じ蔵書で
        取置を引き継がせる(`assign_hold` を再帰的に使う)。誰もいなければ
        取置は消滅し、その蔵書はただ在架に戻る(reservation 側では何もしない)。
        """
        expired = [hold for hold in self.holds if today > hold.expires_at]
        for hold in expired:
            self.holds.remove(hold)
            self.record_event(
                HoldExpired(title_id=self.title_id, copy_id=hold.copy_id, member_id=hold.member_id)
            )
            self.assign_hold(copy_id=hold.copy_id, today=today)

    def holder_for_copy(self, copy_id: uuid.UUID) -> uuid.UUID | None:
        for hold in self.holds:
            if hold.copy_id == copy_id:
                return hold.member_id
        return None

    def _is_waiting_or_holding(self, member_id: uuid.UUID) -> bool:
        return any(r.member_id == member_id for r in self.reservations) or any(
            h.member_id == member_id for h in self.holds
        )
