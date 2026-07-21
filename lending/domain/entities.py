import uuid
from datetime import date

from lending.domain.events import BookLoaned, BookReturned, LoanOverdue
from lending.domain.exceptions import AlreadyReturned, RenewalNotAllowed
from lending.domain.value_objects import STANDARD_LOAN_PERIOD
from shared.domain.entity import Entity


class Loan(Entity):
    def __init__(
        self,
        *,
        loan_id: uuid.UUID,
        member_id: uuid.UUID,
        copy_id: uuid.UUID,
        loaned_at: date,
        due_date: date,
        returned_at: date | None = None,
        renewal_count: int = 0,
        overdue_notified: bool = False,
    ) -> None:
        super().__init__()
        self.id = loan_id
        self.member_id = member_id
        self.copy_id = copy_id
        self.loaned_at = loaned_at
        self.due_date = due_date
        self.returned_at = returned_at
        self.renewal_count = renewal_count
        self.overdue_notified = overdue_notified

    @classmethod
    def start(cls, *, member_id: uuid.UUID, copy_id: uuid.UUID, loaned_at: date) -> "Loan":
        loan = cls(
            loan_id=uuid.uuid4(),
            member_id=member_id,
            copy_id=copy_id,
            loaned_at=loaned_at,
            due_date=STANDARD_LOAN_PERIOD.due_date_from(loaned_at),
        )
        loan.record_event(BookLoaned(loan_id=loan.id, member_id=member_id, copy_id=copy_id))
        return loan

    @property
    def is_returned(self) -> bool:
        return self.returned_at is not None

    def is_overdue(self, today: date) -> bool:
        return not self.is_returned and today > self.due_date

    def return_book(self, *, today: date) -> None:
        if self.is_returned:
            raise AlreadyReturned(self.id)
        self.returned_at = today
        self.record_event(
            BookReturned(
                loan_id=self.id,
                member_id=self.member_id,
                copy_id=self.copy_id,
                returned_at=today,
            )
        )

    def renew(self, *, today: date, has_reservation: bool) -> None:
        if self.is_returned:
            raise AlreadyReturned(self.id)
        if self.renewal_count >= 1:
            raise RenewalNotAllowed(self.id, "loan has already been renewed once")
        if self.is_overdue(today):
            raise RenewalNotAllowed(self.id, "loan is overdue")
        if has_reservation:
            raise RenewalNotAllowed(self.id, "title has a pending reservation")
        self.renewal_count += 1
        self.due_date = STANDARD_LOAN_PERIOD.due_date_from(today)

    def mark_overdue(self) -> None:
        if self.is_returned:
            raise AlreadyReturned(self.id)
        if self.overdue_notified:
            return
        self.overdue_notified = True
        self.record_event(
            LoanOverdue(loan_id=self.id, member_id=self.member_id, copy_id=self.copy_id)
        )
