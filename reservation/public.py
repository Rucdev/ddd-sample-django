"""reservation モジュールの公開 API。他モジュールはここ以外を import してはならない。"""

import uuid

from reservation.application.dto import HoldDTO
from reservation.infrastructure.models import HoldModel, ReservationModel


def get_active_hold_for_copy(copy_id: uuid.UUID) -> HoldDTO | None:
    """lending が「この蔵書は誰かのために取置されているか」を判定するために使う
    (loan_book ユースケース: 取置対象の会員以外には貸し出せない)。
    """
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
    """lending が「対象書誌に予約(待機中のもの)があるか」を判定するために使う
    (renew_loan ユースケース: 予約がある書誌は延長できない)。取置済みの予約は
    ReservationModel から抜けているため、ここではカウントされない。
    """
    return ReservationModel.objects.filter(title_id=title_id).exists()
