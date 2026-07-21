import uuid
from dataclasses import dataclass
from datetime import date


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
    position: int


@dataclass(frozen=True)
class HoldDTO:
    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID
    expires_at: date
