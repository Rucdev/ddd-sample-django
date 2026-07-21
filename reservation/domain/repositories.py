import uuid
from datetime import date
from typing import Protocol

from reservation.domain.entities import ReservationQueue
from reservation.domain.value_objects import Hold


class ReservationQueueRepository(Protocol):
    def find_by_title(self, title_id: uuid.UUID) -> ReservationQueue: ...

    def save(self, queue: ReservationQueue) -> None: ...

    def find_hold_by_copy(self, copy_id: uuid.UUID) -> Hold | None: ...

    def titles_with_expired_holds(self, today: date) -> list[uuid.UUID]: ...
