from django.db import transaction

from kitchen.application.dto import StartCookingInput, TicketDTO
from kitchen.domain.exceptions import TicketNotFound
from kitchen.domain.repositories import TicketRepository
from shared.infrastructure.event_bus import publish


class StartCookingUseCase:
    """調理開始ユースケース。`CookingStarted` の発行で、ordering 側の注文が「調理中」になる。"""

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, data: StartCookingInput) -> TicketDTO:
        with transaction.atomic():
            ticket = self._repository.find_by_id(data.ticket_id)
            if ticket is None:
                raise TicketNotFound(data.ticket_id)

            ticket.start_cooking()
            self._repository.save(ticket)
            publish(ticket.collect_events())

        return TicketDTO.from_entity(ticket)
