import uuid
from dataclasses import dataclass
from datetime import date


# CancelReservationInput / ReservationDTO が (title_id, member_id) をキーにしているのは、
# save() が予約・取置を洗い替える実装のため、行 ID が安定しないことに合わせている
# (reservation/infrastructure/repositories.py 参照)。


@dataclass(frozen=True)
class ReserveTitleInput:
    member_id: uuid.UUID
    title_id: uuid.UUID


@dataclass(frozen=True)
class CancelReservationInput:
    member_id: uuid.UUID
    title_id: uuid.UUID


@dataclass(frozen=True)
class ReservationDTO:
    title_id: uuid.UUID
    member_id: uuid.UUID
    requested_at: date
    position: int  # 待ち行列内の順位(1 始まり)。画面表示用。


@dataclass(frozen=True)
class HoldDTO:
    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID
    expires_at: date
