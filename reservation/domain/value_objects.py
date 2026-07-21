import uuid
from dataclasses import dataclass
from datetime import date

from shared.domain.value_object import ValueObject

HOLD_PERIOD_DAYS = 7


@dataclass(frozen=True)
class Reservation(ValueObject):
    member_id: uuid.UUID
    requested_at: date


@dataclass(frozen=True)
class Hold(ValueObject):
    copy_id: uuid.UUID
    member_id: uuid.UUID
    expires_at: date
