import uuid
from collections.abc import Iterable

from django.db import transaction

from kitchen.domain.entities import Ticket
from kitchen.domain.repositories import TicketRepository
from kitchen.domain.value_objects import TicketItem
from shared.infrastructure.event_bus import publish


class OpenTicketUseCase:
    """注文を受けて調理チケットを作る。ordering の `OrderPlaced` イベント
    (`kitchen/infrastructure/event_handlers.py`)から呼ばれる。

    同じ注文のチケットがすでにあれば何もしない(イベントが二重に届いても安全なように冪等にしておく)。
    """

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, *, order_id: uuid.UUID, items: Iterable[TicketItem]) -> None:
        with transaction.atomic():
            if self._repository.find_by_order(order_id) is not None:
                return
            ticket = Ticket.open(order_id=order_id, items=items)
            self._repository.save(ticket)
            publish(ticket.collect_events())
