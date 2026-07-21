"""Public API of the reservation module. Other modules must only import from here."""

import uuid

from reservation.application.dto import HoldDTO
from reservation.infrastructure.models import HoldModel, ReservationModel


def get_active_hold_for_copy(copy_id: uuid.UUID) -> HoldDTO | None:
    model = HoldModel.objects.filter(copy_id=copy_id).first()
    if model is None:
        return None
    return HoldDTO(
        title_id=model.title_id,
        copy_id=model.copy_id,
        member_id=model.member_id,
        expires_at=model.expires_at,
    )


def has_reservation(title_id: uuid.UUID) -> bool:
    return ReservationModel.objects.filter(title_id=title_id).exists()
