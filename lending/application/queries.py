"""参照系(CQRS の Q)。リポジトリ/エンティティを経由せず ORM を直読みして DTO に詰め替える。

一覧表示のためだけにエンティティを組み立てるのは過剰なので、参照系は素直に ORM から
DTO へ変換してよい、というのが directory-structure.md の方針。
"""

import uuid

from lending.application.dto import LoanDTO
from lending.infrastructure.models import LoanModel


def _to_dto(model: LoanModel) -> LoanDTO:
    return LoanDTO(
        id=model.id,
        member_id=model.member_id,
        copy_id=model.copy_id,
        loaned_at=model.loaned_at,
        due_date=model.due_date,
        returned_at=model.returned_at,
        renewal_count=model.renewal_count,
    )


def list_loans(*, active_only: bool = False) -> list[LoanDTO]:
    queryset = LoanModel.objects.order_by("-loaned_at")
    if active_only:
        queryset = queryset.filter(returned_at__isnull=True)
    return [_to_dto(model) for model in queryset]


def list_loans_for_member(member_id: uuid.UUID) -> list[LoanDTO]:
    queryset = LoanModel.objects.filter(member_id=member_id).order_by("-loaned_at")
    return [_to_dto(model) for model in queryset]


def get_loan(loan_id: uuid.UUID) -> LoanDTO | None:
    model = LoanModel.objects.filter(id=loan_id).first()
    return _to_dto(model) if model else None
