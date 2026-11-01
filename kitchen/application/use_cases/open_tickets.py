import uuid
from collections.abc import Iterable

from django.db import transaction

from kitchen.domain.entities import Ticket
from kitchen.domain.repositories import TicketRepository
from kitchen.domain.value_objects import TicketItem
from shared.infrastructure.event_bus import publish


class OpenTicketsUseCase:
    """注文を受けて、明細 1 行ごとに調理チケットを作る。ordering の `OrderPlaced` イベント
    (`kitchen/infrastructure/event_handlers.py`)から呼ばれる。

    `items` は (明細の番号, 何を何個) の組。同じ注文のチケットがすでにあれば何もしない
    (イベントが二重に届いても安全なように冪等にしておく)。
    """

    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    def execute(self, *, order_id: uuid.UUID, items: Iterable[tuple[int, TicketItem]]) -> None:
        with transaction.atomic():
            if self._repository.find_by_order(order_id):
                return
            for line_no, item in items:
                ticket = Ticket.open(order_id=order_id, line_no=line_no, item=item)
                self._repository.save(ticket)
                publish(ticket.collect_events())
