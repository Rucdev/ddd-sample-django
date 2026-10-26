import uuid
from typing import Protocol

from kitchen.domain.entities import Ticket


class TicketRepository(Protocol):
    """`Ticket` 集約の永続化を抽象化するリポジトリ。"""

    def save(self, ticket: Ticket) -> None: ...

    def find_by_id(self, ticket_id: uuid.UUID) -> Ticket | None: ...

    def find_by_order(self, order_id: uuid.UUID) -> Ticket | None: ...
