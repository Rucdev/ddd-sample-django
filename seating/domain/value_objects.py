from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from seating.domain.exceptions import InvalidSeatLayout
from shared.domain.value_object import ValueObject


class SeatStatus(StrEnum):
    """座席のステータス。遷移は Seat エンティティのメソッドだけが行う。

              予約            着席
    AVAILABLE ────▶ RESERVED ────▶ OCCUPIED
        ▲  │ ◀──────────           │
        │  │    予約取消            │
        │  └───────────────────────▶│ 案内(予約なしで座る)
        └───────────────────────────┘
                    退席
    """

    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"


@dataclass(frozen=True)
class SeatPosition(ValueObject):
    """エリアの中での座席の位置。画面の見取り図で何行何列目に描くか(1 始まり)。"""

    row: int
    col: int

    def __post_init__(self) -> None:
        if self.row < 1 or self.col < 1:
            raise InvalidSeatLayout(f"Seat position must be 1 or more (row={self.row}, col={self.col})")


@dataclass(frozen=True)
class SeatSpec(ValueObject):
    """座席構成ファイルに書かれた 1 席分の定義。席の「形」だけを持ち、ステータスは持たない。"""

    code: str
    area_code: str
    capacity: int
    position: SeatPosition

    def __post_init__(self) -> None:
        if not self.code:
            raise InvalidSeatLayout("Seat code must not be empty")
        if self.capacity < 1:
            raise InvalidSeatLayout(f"Seat {self.code} must seat at least 1 person")


@dataclass(frozen=True)
class AreaSpec(ValueObject):
    """座席構成ファイルに書かれたエリア(カウンター、テラス など)。並び順はファイルでの順番。"""

    code: str
    name: str
    display_order: int

    def __post_init__(self) -> None:
        if not self.code:
            raise InvalidSeatLayout("Area code must not be empty")


@dataclass(frozen=True)
class SeatLayout(ValueObject):
    """座席構成。座席構成ファイル 1 つ分(seating/CONTEXT.md 参照)。

    ファイルの形式(YAML)には依存しない。読み込みは infrastructure/layout_file.py が行い、
    ここでは「構成として成り立っているか」だけを検査する。
    """

    areas: tuple[AreaSpec, ...]
    seats: tuple[SeatSpec, ...]

    def __init__(self, areas: Iterable[AreaSpec], seats: Iterable[SeatSpec]) -> None:
        object.__setattr__(self, "areas", tuple(areas))
        object.__setattr__(self, "seats", tuple(seats))
        self._validate()

    def _validate(self) -> None:
        area_codes = [area.code for area in self.areas]
        _ensure_unique("area code", area_codes)
        _ensure_unique("seat code", [seat.code for seat in self.seats])
        for seat in self.seats:
            if seat.area_code not in area_codes:
                raise InvalidSeatLayout(f"Seat {seat.code} belongs to unknown area {seat.area_code}")
        _ensure_unique(
            "seat position",
            [f"{s.area_code} row {s.position.row} col {s.position.col}" for s in self.seats],
        )

    def seat(self, code: str) -> SeatSpec | None:
        return next((seat for seat in self.seats if seat.code == code), None)


def _ensure_unique(label: str, values: list[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise InvalidSeatLayout(f"Duplicate {label}: {', '.join(duplicates)}")
