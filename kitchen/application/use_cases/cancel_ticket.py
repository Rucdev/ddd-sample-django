import uuid

from django.db import transaction

from kitchen.domain.repositories import TicketRepository
from shared.infrastructure.event_bus import publish


class CancelTicketUseCase:
    """注文のキャンセルを受けてチケットを取り消す。ordering の `OrderCancelled` イベントから呼ばれる。"""

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, *, order_id: uuid.UUID) -> None:
        with transaction.atomic():
            ticket = self._repository.find_by_order(order_id)
            if ticket is None:
                return
            ticket.cancel()
            self._repository.save(ticket)
            publish(ticket.collect_events())
