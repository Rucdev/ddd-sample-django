import uuid

from seating.domain.events import SeatOccupied, SeatVacated
from seating.domain.exceptions import InvalidSeatTransition
from seating.domain.value_objects import SeatPosition, SeatSpec, SeatStatus
from shared.domain.entity import Entity


class Seat(Entity):
    """座席。集約ルート。

    席の「形」(エリア・定員・位置)は座席構成ファイルが決め、ここでは書き換えない
    (`apply_spec` で構成ファイルの内容に合わせるだけ)。席ごとに持つのはステータスで、
    空き → 予約中 → 使用中 → 空き の遷移ルールをこのクラスが守る(seating/CONTEXT.md 参照)。
    """

    def __init__(
        self,
        *,
        seat_id: uuid.UUID,
        code: str,
        area_code: str,
        capacity: int,
        position: SeatPosition,
        status: SeatStatus = SeatStatus.AVAILABLE,
    ) -> None:
        super().__init__()
        self.id = seat_id
        self.code = code
        self.area_code = area_code
        self.capacity = capacity
        self.position = position
        self.status = status

    @classmethod
    def install(cls, spec: SeatSpec) -> "Seat":
        """座席構成に新しく現れた席を置く。置いたばかりの席は空き。"""
        return cls(
            seat_id=uuid.uuid4(),
            code=spec.code,
            area_code=spec.area_code,
            capacity=spec.capacity,
            position=spec.position,
        )

    def apply_spec(self, spec: SeatSpec) -> None:
        """座席構成の変更(エリアの移動・定員・位置)を反映する。ステータスはそのまま。"""
        self.area_code = spec.area_code
        self.capacity = spec.capacity
        self.position = spec.position

    def matches(self, spec: SeatSpec) -> bool:
        return (self.area_code, self.capacity, self.position) == (
            spec.area_code,
            spec.capacity,
            spec.position,
        )

    @property
    def is_removable(self) -> bool:
        """座席構成から外してよいか。予約中・使用中の席は撤去できない。"""
        return self.status == SeatStatus.AVAILABLE

    # ---- ステータスの遷移 ----

    def reserve(self) -> None:
        self._transition({SeatStatus.AVAILABLE}, SeatStatus.RESERVED, "be reserved")

    def cancel_reservation(self) -> None:
        self._transition({SeatStatus.RESERVED}, SeatStatus.AVAILABLE, "cancel reservation")

    def occupy(self) -> None:
        """お客様が座る。予約していたお客様の着席と、予約なしの案内の両方。席の利用が始まる。"""
        self._transition({SeatStatus.AVAILABLE, SeatStatus.RESERVED}, SeatStatus.OCCUPIED, "be occupied")
        self.record_event(SeatOccupied(seat_id=self.id, seat_code=self.code))

    def vacate(self) -> None:
        """お客様が席を立ち、次のお客様を通せるようになる。席の利用が終わる。"""
        self._transition({SeatStatus.OCCUPIED}, SeatStatus.AVAILABLE, "be vacated")
        self.record_event(SeatVacated(seat_id=self.id, seat_code=self.code))

    def _transition(self, allowed: set[SeatStatus], to: SeatStatus, action: str) -> None:
        if self.status not in allowed:
            raise InvalidSeatTransition(self.code, self.status, action)
        self.status = to
