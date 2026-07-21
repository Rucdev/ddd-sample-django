import uuid

from lending.domain.exceptions import LoanLimitExceeded
from lending.domain.repositories import LoanRepository

# 貸出上限(同時に借りられる冊数)。標準は 5 冊。
DEFAULT_LOAN_LIMIT = 5


class LoanPolicy:
    """ドメインサービス。1 つのエンティティに閉じない判定(会員をまたいだ貸出冊数の集計)
    を担う。リポジトリの集計メソッドを使うので、Loan エンティティ自身には持たせない。
    """

    def __init__(self, loan_repository: LoanRepository, limit: int = DEFAULT_LOAN_LIMIT) -> None:
        self._loan_repository = loan_repository
        self._limit = limit

    def ensure_member_can_borrow(self, member_id: uuid.UUID) -> None:
        if self._loan_repository.count_active_by_member(member_id) >= self._limit:
            raise LoanLimitExceeded(member_id, self._limit)
