"""参照系(CQRS の Q)。リポジトリ/集約を経由せず ORM を直読みして DTO に詰め替える。"""

import uuid

from reservation.application.dto import HoldDTO, ReservationDTO
from reservation.infrastructure.models import HoldModel, ReservationModel


def _to_reservation_dto(model: ReservationModel, position: int) -> ReservationDTO:
    return ReservationDTO(
        title_id=model.title_id,
        member_id=model.member_id,
        requested_at=model.requested_at,
        position=position,
    )


def _to_hold_dto(model: HoldModel) -> HoldDTO:
    return HoldDTO(
        title_id=model.title_id,
        copy_id=model.copy_id,
        member_id=model.member_id,
        expires_at=model.expires_at,
    )


def list_reservations() -> list[ReservationDTO]:
    """全書誌分の予約一覧(画面の一覧表示用)。書誌ごとに申込順で 1 から順位を振り直す。"""
    queryset = ReservationModel.objects.order_by("title_id", "requested_at")
    positions: dict[uuid.UUID, int] = {}
    result = []
    for model in queryset:
        positions[model.title_id] = positions.get(model.title_id, 0) + 1
        result.append(_to_reservation_dto(model, positions[model.title_id]))
    return result


def list_reservations_for_title(title_id: uuid.UUID) -> list[ReservationDTO]:
    queryset = ReservationModel.objects.filter(title_id=title_id).order_by("requested_at")
    return [_to_reservation_dto(model, position) for position, model in enumerate(queryset, start=1)]


def list_holds() -> list[HoldDTO]:
    return [_to_hold_dto(model) for model in HoldModel.objects.order_by("title_id")]
