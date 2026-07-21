import uuid
from dataclasses import dataclass
from datetime import date

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class BookLoaned(DomainEvent):
    """貸出が成立したことを表すドメインイベント。"""

    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class BookReturned(DomainEvent):
    """返却されたことを表すドメインイベント。reservation モジュールが購読し、
    予約待ちの先頭会員へ取置を作る(reservation/infrastructure/event_handlers.py)。

    `returned_at` は「返却が成立した業務上の日付」。基底クラスの `occurred_at`
    (イベント生成時刻)とは別に持つ。取置期限(+7日)の起算日として使うため、
    テストで `today` を差し替えて呼んだ場合でも実際の日付とずれないようにしている。
    """

    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID
    returned_at: date


@dataclass(frozen=True, kw_only=True)
class LoanOverdue(DomainEvent):
    """延滞が確定したことを表すドメインイベント。members モジュールが購読し、
    会員を貸出停止にする(members/event_handlers.py)。
    """

    loan_id: uuid.UUID
    member_id: uuid.UUID
    copy_id: uuid.UUID
