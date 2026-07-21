import uuid
from typing import Protocol

from lending.domain.entities import Loan


class LoanRepository(Protocol):
    """`Loan` 集約の永続化を抽象化するリポジトリ。domain 層はこの Protocol にだけ依存し、
    実装(ORM を使う `DjangoLoanRepository`)には依存しない。テストではインメモリの
    フェイク実装(`lending/tests/test_application/fakes.py`)に差し替えられる。
    """

    def save(self, loan: Loan) -> None: ...

    def find_by_id(self, loan_id: uuid.UUID) -> Loan | None: ...

    def count_active_by_member(self, member_id: uuid.UUID) -> int: ...

    def count_overdue_by_member(self, member_id: uuid.UUID) -> int: ...

    def find_active_by_copy(self, copy_id: uuid.UUID) -> Loan | None: ...
