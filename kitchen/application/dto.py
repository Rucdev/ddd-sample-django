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
class TicketItemDTO:
    name: str
    quantity: int


@dataclass(frozen=True)
class TicketDTO:
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    items: tuple[TicketItemDTO, ...]

    @classmethod
    def from_entity(cls, ticket: Ticket) -> "TicketDTO":
        return cls(
            id=ticket.id,
            order_id=ticket.order_id,
            status=ticket.status.value,
            items=tuple(TicketItemDTO(name=i.name, quantity=i.quantity) for i in ticket.items),
        )
