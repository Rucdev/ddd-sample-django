from catalog.public import get_copy
from lending.domain.events import BookReturned
from reservation.application.use_cases.assign_hold import AssignHoldUseCase
from reservation.infrastructure.repositories import DjangoReservationQueueRepository


def handle_book_returned(event: BookReturned) -> None:
    copy = get_copy(event.copy_id)
    if copy is None:
        return

    use_case = AssignHoldUseCase(repository=DjangoReservationQueueRepository())
    use_case.execute(title_id=copy.title_id, copy_id=event.copy_id, today=event.returned_at)
