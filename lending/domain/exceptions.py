import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError


class LendingError(DomainError):
    """Base class for lending domain errors."""


class LoanNotFound(LendingError, NotFoundError):
    def __init__(self, loan_id: uuid.UUID) -> None:
        self.loan_id = loan_id
        super().__init__(f"Loan {loan_id} was not found")


class LoanLimitExceeded(LendingError, ConflictError):
    def __init__(self, member_id: uuid.UUID, limit: int) -> None:
        self.member_id = member_id
        self.limit = limit
        super().__init__(f"Member {member_id} has reached the loan limit of {limit}")


class RenewalNotAllowed(LendingError, ConflictError):
    def __init__(self, loan_id: uuid.UUID, reason: str) -> None:
        self.loan_id = loan_id
        self.reason = reason
        super().__init__(f"Loan {loan_id} cannot be renewed: {reason}")


class MemberNotLoanable(LendingError, ConflictError):
    def __init__(self, member_id: uuid.UUID) -> None:
        self.member_id = member_id
        super().__init__(f"Member {member_id} is not eligible to borrow books")


class CopyNotLoanable(LendingError, ConflictError):
    def __init__(self, copy_id: uuid.UUID, reason: str) -> None:
        self.copy_id = copy_id
        self.reason = reason
        super().__init__(f"Copy {copy_id} cannot be loaned: {reason}")


class AlreadyReturned(LendingError, ConflictError):
    def __init__(self, loan_id: uuid.UUID) -> None:
        self.loan_id = loan_id
        super().__init__(f"Loan {loan_id} has already been returned")
