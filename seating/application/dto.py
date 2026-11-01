import uuid
from dataclasses import dataclass

from seating.domain.entities import Seat


@dataclass(frozen=True)
class SeatCommandInput:
    """予約・予約取消・着席(案内)・退席に共通の入力。対象の席を指すだけ。"""

    seat_id: uuid.UUID


@dataclass(frozen=True)
class SeatDTO:
    id: uuid.UUID
    code: str
    area_code: str
    capacity: int
    row: int
    col: int
    status: str

    @classmethod
    def from_entity(cls, seat: Seat) -> "SeatDTO":
        return cls(
            id=seat.id,
            code=seat.code,
            area_code=seat.area_code,
            capacity=seat.capacity,
            row=seat.position.row,
            col=seat.position.col,
            status=seat.status.value,
        )


@dataclass(frozen=True)
class ApplySeatLayoutResult:
    installed: tuple[str, ...]  # 席コード
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: int
