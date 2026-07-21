import uuid

from lending.domain.entities import Loan


class FakeLoanRepository:
    def __init__(self) -> None:
        self._loans: dict[uuid.UUID, Loan] = {}

    def save(self, loan: Loan) -> None:
        self._loans[loan.id] = loan

    def find_by_id(self, loan_id: uuid.UUID) -> Loan | None:
        return self._loans.get(loan_id)

    def count_active_by_member(self, member_id: uuid.UUID) -> int:
        return sum(
            1
            for loan in self._loans.values()
            if loan.member_id == member_id and not loan.is_returned
        )

    def count_overdue_by_member(self, member_id: uuid.UUID) -> int:
        return sum(
            1
            for loan in self._loans.values()
            if loan.member_id == member_id and not loan.is_returned and loan.overdue_notified
        )

    def find_active_by_copy(self, copy_id: uuid.UUID) -> Loan | None:
        for loan in self._loans.values():
            if loan.copy_id == copy_id and not loan.is_returned:
                return loan
        return None
