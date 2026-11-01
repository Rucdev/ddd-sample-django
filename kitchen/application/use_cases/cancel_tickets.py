import uuid

from django.db import transaction

from kitchen.domain.repositories import TicketRepository
from shared.infrastructure.event_bus import publish


class CancelTicketsUseCase:
    """注文のキャンセルを受けて、その注文のチケットをすべて取り消す。ordering の
    `OrderCancelled` イベントから呼ばれる。
    """

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, *, order_id: uuid.UUID) -> None:
        with transaction.atomic():
            for ticket in self._repository.find_by_order(order_id):
                ticket.cancel()
                self._repository.save(ticket)
                publish(ticket.collect_events())
