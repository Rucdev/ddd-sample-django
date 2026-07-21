import uuid
from dataclasses import dataclass
from datetime import date

from lending.domain.entities import Loan


# 各ユースケースの入力 DTO。presentation 層(Form / Serializer)が形式チェック済みの値を
# ここに詰め替えてユースケースへ渡す。


@dataclass(frozen=True)
class LoanBookInput:
    member_id: uuid.UUID
    copy_id: uuid.UUID


@dataclass(frozen=True)
class ReturnBookInput:
    loan_id: uuid.UUID


@dataclass(frozen=True)
class RenewLoanInput:
    loan_id: uuid.UUID


@dataclass(frozen=True)
class LoanDTO:
    """ユースケースの出力・画面表示用の DTO。エンティティや ORM モデルをそのまま
    presentation 層に渡さないための境界。
    """

    id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID
    loaned_at: date
    due_date: date
    returned_at: date | None
    renewal_count: int

    @classmethod
    def from_entity(cls, loan: Loan) -> "LoanDTO":
        return cls(
            id=loan.id,
            member_id=loan.member_id,
            copy_id=loan.copy_id,
            loaned_at=loan.loaned_at,
            due_date=loan.due_date,
            returned_at=loan.returned_at,
            renewal_count=loan.renewal_count,
        )
