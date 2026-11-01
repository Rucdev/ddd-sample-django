import uuid
from collections.abc import Iterable

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# kitchen と同じパターン: shared.domain.exceptions の NotFoundError / ConflictError も
# 多重継承しておき、shared/infrastructure/exception_handler.py で 404 / 409 に変換させる。


class SeatingError(DomainError):
    """Base class for seating domain errors."""


class SeatNotFound(SeatingError, NotFoundError):
    def __init__(self, seat_id: uuid.UUID) -> None:
        self.seat_id = seat_id
        super().__init__(f"Seat {seat_id} was not found")


class InvalidSeatTransition(SeatingError, ConflictError):
    def __init__(self, code: str, current: str, action: str) -> None:
        self.code = code
        self.current = current
        self.action = action
        super().__init__(f"Seat {code} cannot {action} while {current}")


class InvalidSeatLayout(SeatingError):
    """座席構成ファイルの中身が構成として成り立っていない(コードの重複、位置の重なりなど)。"""


class SeatsInUse(SeatingError, ConflictError):
    """座席構成から消えた席が、まだ予約中・使用中で撤去できない。"""

    def __init__(self, codes: Iterable[str]) -> None:
        self.codes = tuple(sorted(codes))
        super().__init__(f"Seats still reserved or occupied cannot be removed: {', '.join(self.codes)}")
