import uuid
from datetime import date
from typing import Protocol

from reservation.domain.entities import ReservationQueue
from reservation.domain.value_objects import Hold


class ReservationQueueRepository(Protocol):
    """`ReservationQueue` 集約の永続化を抽象化するリポジトリ。

    `find_by_title` はその書誌の予約待ち行列がまだ 1 件も無くても None ではなく
    「空の ReservationQueue」を返す設計にしている。予約待ち行列が無い状態を
    自然に「空の集約」として扱えるため、呼び出し側の None チェックが要らない。
    """

    def find_by_title(self, title_id: uuid.UUID) -> ReservationQueue: ...

    def save(self, queue: ReservationQueue) -> None: ...

    def find_hold_by_copy(self, copy_id: uuid.UUID) -> Hold | None: ...

    def titles_with_expired_holds(self, today: date) -> list[uuid.UUID]: ...
