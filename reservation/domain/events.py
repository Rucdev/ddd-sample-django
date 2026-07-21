import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class HoldReady(DomainEvent):
    """取置が成立したことを表すドメインイベント。返却をきっかけに
    `ReservationQueue.assign_hold` が発行する。"""

    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class HoldExpired(DomainEvent):
    """取置が期限切れで失効したことを表すドメインイベント。"""

    title_id: uuid.UUID
    copy_id: uuid.UUID
    member_id: uuid.UUID
