from django.db import transaction

from kitchen.application.dto import CompleteCookingInput, TicketDTO
from kitchen.domain.exceptions import TicketNotFound
from kitchen.domain.repositories import TicketRepository
from shared.infrastructure.event_bus import publish


class CompleteCookingUseCase:
    """調理完了ユースケース。`CookingCompleted` の発行で、ordering 側の注文が「受取可」になる。"""

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, data: CompleteCookingInput) -> TicketDTO:
        with transaction.atomic():
            ticket = self._repository.find_by_id(data.ticket_id)
            if ticket is None:
                raise TicketNotFound(data.ticket_id)

            ticket.complete()
            self._repository.save(ticket)
            publish(ticket.collect_events())

        return TicketDTO.from_entity(ticket)
