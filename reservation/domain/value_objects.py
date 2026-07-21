import uuid
from dataclasses import dataclass
from datetime import date

from shared.domain.value_object import ValueObject

# 取置期限(取置成立から何日で失効するか)。標準は 7 日。
HOLD_PERIOD_DAYS = 7


@dataclass(frozen=True)
class Reservation(ValueObject):
    """予約 1 件。値オブジェクト。集約(ReservationQueue)内部でのみ使い、
    それ自体に識別子は持たせていない(会員 ID が書誌内で一意なキーになる)。
    """

    member_id: uuid.UUID
    requested_at: date


@dataclass(frozen=True)
class Hold(ValueObject):
    """取置。返却された蔵書(個体)が特定の会員のために確保された状態。"""

    copy_id: uuid.UUID
    member_id: uuid.UUID
    expires_at: date
