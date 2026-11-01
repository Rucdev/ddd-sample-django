import uuid

from kitchen.domain.entities import Ticket
from kitchen.domain.value_objects import TicketItem, TicketStatus
from kitchen.infrastructure.models import TicketModel


class DjangoTicketRepository:
    """`TicketRepository` の Django ORM 実装。`Ticket` エンティティ ⇔ `TicketModel` の変換をここに閉じ込める。"""

    def save(self, ticket: Ticket) -> None:
        TicketModel.objects.update_or_create(
            id=ticket.id,
            defaults={
                "order_id": ticket.order_id,
                "line_no": ticket.line_no,
                "name": ticket.item.name,
                "quantity": ticket.item.quantity,
                "status": ticket.status.value,
            },
        )

    def find_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        model = TicketModel.objects.filter(id=ticket_id).first()
        return self._to_entity(model) if model else None

    def find_by_order(self, order_id: uuid.UUID) -> list[Ticket]:
        return [
            self._to_entity(model)
            for model in TicketModel.objects.filter(order_id=order_id).order_by("line_no")
        ]

    @staticmethod
    def _to_entity(model: TicketModel) -> Ticket:
        return Ticket(
            ticket_id=model.id,
            order_id=model.order_id,
            line_no=model.line_no,
            item=TicketItem(name=model.name, quantity=model.quantity),
            status=TicketStatus(model.status),
        )
