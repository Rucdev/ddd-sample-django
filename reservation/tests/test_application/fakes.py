import uuid
from datetime import date

from reservation.domain.entities import ReservationQueue
from reservation.domain.value_objects import Hold


class FakeReservationQueueRepository:
    def __init__(self) -> None:
        self._queues: dict[uuid.UUID, ReservationQueue] = {}

    def find_by_title(self, title_id: uuid.UUID) -> ReservationQueue:
        queue = self._queues.get(title_id)
        if queue is None:
            return ReservationQueue(title_id=title_id)
        return ReservationQueue(
            title_id=title_id,
            reservations=list(queue.reservations),
            holds=list(queue.holds),
        )

    def save(self, queue: ReservationQueue) -> None:
        self._queues[queue.title_id] = queue

    def find_hold_by_copy(self, copy_id: uuid.UUID) -> Hold | None:
        for queue in self._queues.values():
            for hold in queue.holds:
                if hold.copy_id == copy_id:
                    return hold
        return None

    def titles_with_expired_holds(self, today: date) -> list[uuid.UUID]:
        return [
            title_id
            for title_id, queue in self._queues.items()
            if any(today > hold.expires_at for hold in queue.holds)
        ]
