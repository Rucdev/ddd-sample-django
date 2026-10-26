import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CookingStarted(DomainEvent):
    """調理が始まったことを表すドメインイベント。ordering モジュールが購読し、
    注文を「調理中」にする(ordering/infrastructure/event_handlers.py)。
    """

    ticket_id: uuid.UUID
    order_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class CookingCompleted(DomainEvent):
    """調理が終わったことを表すドメインイベント。ordering モジュールが購読し、
    注文を「受取可」にする。
    """

    ticket_id: uuid.UUID
    order_id: uuid.UUID
