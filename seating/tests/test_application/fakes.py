import copy
import uuid
from collections.abc import Iterable

from seating.domain.entities import Seat
from seating.domain.value_objects import AreaSpec


class FakeSeatRepository:
    def __init__(self) -> None:
        self.seats: dict[uuid.UUID, Seat] = {}
        self.lock_count = 0  # for_update=True で読まれた回数(ロックを取ったかの確認用)

    def save(self, seat: Seat) -> None:
        self.seats[seat.id] = copy.deepcopy(seat)

    def remove(self, seat: Seat) -> None:
        del self.seats[seat.id]

    def find_by_id(self, seat_id: uuid.UUID, *, for_update: bool = False) -> Seat | None:
        self.lock_count += for_update
        seat = self.seats.get(seat_id)
        return copy.deepcopy(seat) if seat else None

    def find_all(self, *, for_update: bool = False) -> list[Seat]:
        self.lock_count += for_update
        return [copy.deepcopy(seat) for seat in self.seats.values()]

    def by_code(self, code: str) -> Seat:
        return next(seat for seat in self.seats.values() if seat.code == code)


class FakeAreaRepository:
    def __init__(self) -> None:
        self.areas: dict[str, AreaSpec] = {}

    def save_all(self, areas: Iterable[AreaSpec]) -> None:
        for area in areas:
            self.areas[area.code] = area

    def remove_except(self, codes: Iterable[str]) -> None:
        keep = set(codes)
        self.areas = {code: area for code, area in self.areas.items() if code in keep}
