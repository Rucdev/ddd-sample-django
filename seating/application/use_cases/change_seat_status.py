"""席のステータスを動かすユースケース(予約・予約取消・着席・退席)。

4 つとも「席を取り出す → エンティティのメソッドで遷移させる → 保存する」だけで、違うのは
呼ぶメソッドだけなので 1 ファイルにまとめている。遷移してよいかの判定は `Seat` が行う。
"""

from collections.abc import Callable

from django.db import transaction

from seating.application.dto import SeatCommandInput, SeatDTO
from seating.domain.entities import Seat
from seating.domain.exceptions import SeatNotFound
from seating.domain.repositories import SeatRepository
from shared.infrastructure.event_bus import publish


class _ChangeSeatStatusUseCase:
    _action: Callable[[Seat], None]

    def __init__(self, repository: SeatRepository) -> None:
        self._repository = repository

    def execute(self, data: SeatCommandInput) -> SeatDTO:
        with transaction.atomic():
            seat = self._repository.find_by_id(data.seat_id)
            if seat is None:
                raise SeatNotFound(data.seat_id)

            type(self)._action(seat)
            self._repository.save(seat)
            publish(seat.collect_events())

        return SeatDTO.from_entity(seat)


class ReserveSeatUseCase(_ChangeSeatStatusUseCase):
    """予約: 空き → 予約中。"""

    _action = Seat.reserve


class CancelSeatReservationUseCase(_ChangeSeatStatusUseCase):
    """予約取消: 予約中 → 空き。"""

    _action = Seat.cancel_reservation


class OccupySeatUseCase(_ChangeSeatStatusUseCase):
    """着席(予約あり)/ 案内(予約なし): 予約中・空き → 使用中。"""

    _action = Seat.occupy


class VacateSeatUseCase(_ChangeSeatStatusUseCase):
    """退席: 使用中 → 空き。"""

    _action = Seat.vacate
