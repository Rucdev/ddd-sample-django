import uuid
from datetime import date

from reservation.domain.entities import ReservationQueue
from reservation.domain.value_objects import Hold, Reservation
from reservation.infrastructure.models import HoldModel, ReservationModel


class DjangoReservationQueueRepository:
    def find_by_title(self, title_id: uuid.UUID) -> ReservationQueue:
        reservations = [
            Reservation(member_id=model.member_id, requested_at=model.requested_at)
            for model in ReservationModel.objects.filter(title_id=title_id).order_by(
                "requested_at"
            )
        ]
        holds = [
            Hold(copy_id=model.copy_id, member_id=model.member_id, expires_at=model.expires_at)
            for model in HoldModel.objects.filter(title_id=title_id)
        ]
        return ReservationQueue(title_id=title_id, reservations=reservations, holds=holds)

    def save(self, queue: ReservationQueue) -> None:
        ReservationModel.objects.filter(title_id=queue.title_id).delete()
        ReservationModel.objects.bulk_create(
            ReservationModel(
                title_id=queue.title_id,
                member_id=reservation.member_id,
                requested_at=reservation.requested_at,
            )
            for reservation in queue.reservations
        )

        HoldModel.objects.filter(title_id=queue.title_id).delete()
        HoldModel.objects.bulk_create(
            HoldModel(
                title_id=queue.title_id,
                copy_id=hold.copy_id,
                member_id=hold.member_id,
                expires_at=hold.expires_at,
            )
            for hold in queue.holds
        )

    def find_hold_by_copy(self, copy_id: uuid.UUID) -> Hold | None:
        model = HoldModel.objects.filter(copy_id=copy_id).first()
        if model is None:
            return None
        return Hold(copy_id=model.copy_id, member_id=model.member_id, expires_at=model.expires_at)

    def titles_with_expired_holds(self, today: date) -> list[uuid.UUID]:
        return list(
            HoldModel.objects.filter(expires_at__lt=today)
            .values_list("title_id", flat=True)
            .distinct()
        )
