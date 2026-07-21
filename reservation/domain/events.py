import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class HoldReady(DomainEvent):
    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class HoldExpired(DomainEvent):
    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID
