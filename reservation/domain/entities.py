import uuid
from datetime import date, timedelta

from reservation.domain.events import HoldExpired, HoldReady
from reservation.domain.exceptions import DuplicateReservation, NotReserved
from reservation.domain.value_objects import HOLD_PERIOD_DAYS, Hold, Reservation
from shared.domain.entity import Entity


class ReservationQueue(Entity):
    """Aggregate root for a single title's reservation queue and its holds.

    Keyed by title_id: one queue per title, holding both the FIFO list of
    members still waiting and the holds already handed out for copies of
    that title.
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
        if self._is_waiting_or_holding(member_id):
            raise DuplicateReservation(self.title_id, member_id)
        self.reservations.append(Reservation(member_id=member_id, requested_at=today))

    def cancel(self, member_id: uuid.UUID) -> None:
        for reservation in self.reservations:
            if reservation.member_id == member_id:
                self.reservations.remove(reservation)
                return
        raise NotReserved(self.title_id, member_id)

    def assign_hold(self, *, copy_id: uuid.UUID, today: date) -> Hold | None:
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
