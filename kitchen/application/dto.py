import uuid
from dataclasses import dataclass

from kitchen.domain.entities import Ticket


@dataclass(frozen=True)
class StartCookingInput:
    ticket_id: uuid.UUID


@dataclass(frozen=True)
class CompleteCookingInput:
    ticket_id: uuid.UUID


@dataclass(frozen=True)
class TicketDTO:
    id: uuid.UUID
    order_id: uuid.UUID
    line_no: int
    name: str
    quantity: int
    status: str

    @classmethod
    def from_entity(cls, ticket: Ticket) -> "TicketDTO":
        return cls(
            id=ticket.id,
            order_id=ticket.order_id,
            line_no=ticket.line_no,
            name=ticket.item.name,
            quantity=ticket.item.quantity,
            status=ticket.status.value,
        )
