"""lending モジュールの公開 API。他モジュールはここ以外(models・domain・application 等)を
import してはならない。関数と DTO(dataclass)だけを公開し、ORM モデルやエンティティは
返さない。
"""

import uuid

from lending.infrastructure.repositories import DjangoLoanRepository


def count_overdue_loans(member_id: uuid.UUID) -> int:
    """members モジュールが「延滞中の貸出がすべて返却されたか」を判定するために使う
    (延滞解除 = 貸出停止解除の条件)。
    """
    return DjangoLoanRepository().count_overdue_by_member(member_id)
