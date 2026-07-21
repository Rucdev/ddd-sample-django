from lending.domain.events import BookReturned, LoanOverdue
from lending.public import count_overdue_loans
from members.public import reinstate_member, suspend_member


def handle_loan_overdue(event: LoanOverdue) -> None:
    suspend_member(event.member_id)


def handle_book_returned(event: BookReturned) -> None:
    if count_overdue_loans(event.member_id) == 0:
        reinstate_member(event.member_id)
