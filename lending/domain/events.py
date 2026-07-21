import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class BookLoaned(DomainEvent):
    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class BookReturned(DomainEvent):
    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class LoanOverdue(DomainEvent):
    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID
