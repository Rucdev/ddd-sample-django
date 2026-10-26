import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# ordering と同じパターン: shared.domain.exceptions の NotFoundError / ConflictError も
# 多重継承しておくことで、shared/infrastructure/exception_handler.py が kitchen を
# 個別に知らなくても 404 / 409 への変換を行える。


class KitchenError(DomainError):
    """Base class for kitchen domain errors."""


class TicketNotFound(KitchenError, NotFoundError):
    def __init__(self, ticket_id: uuid.UUID) -> None:
        self.ticket_id = ticket_id
        super().__init__(f"Ticket {ticket_id} was not found")


class InvalidTicketTransition(KitchenError, ConflictError):
    def __init__(self, ticket_id: uuid.UUID, current: str, action: str) -> None:
        self.ticket_id = ticket_id
        self.current = current
        self.action = action
        super().__init__(f"Ticket {ticket_id} cannot {action} while {current}")
