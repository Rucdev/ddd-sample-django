"""Public API of the lending module. Other modules must only import from here."""

import uuid

from lending.infrastructure.repositories import DjangoLoanRepository


def count_overdue_loans(member_id: uuid.UUID) -> int:
    return DjangoLoanRepository().count_overdue_by_member(member_id)
