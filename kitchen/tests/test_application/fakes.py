import copy
import uuid

from kitchen.domain.entities import Ticket


class FakeTicketRepository:
    def __init__(self) -> None:
        self._tickets: dict[uuid.UUID, Ticket] = {}

    def save(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = copy.deepcopy(ticket)

    def find_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        ticket = self._tickets.get(ticket_id)
        return copy.deepcopy(ticket) if ticket else None

    def find_by_order(self, order_id: uuid.UUID) -> Ticket | None:
        for ticket in self._tickets.values():
            if ticket.order_id == order_id:
                return copy.deepcopy(ticket)
        return None
