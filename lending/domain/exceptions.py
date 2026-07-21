import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# lending 独自の例外は shared.domain.exceptions の NotFoundError / ConflictError も
# 多重継承しておく。presentation 層(DRF の exception handler)はこの共通基底だけを見て
# 404 / 409 に変換するので、lending の例外を個別に知らなくて済む(shared → 各モジュール
# への依存が生まれない)。同時に LendingError を継いでいるので、lending の view/API 側は
# 「lending のドメイン例外はまとめて捕まえる」という書き方もできる。


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
