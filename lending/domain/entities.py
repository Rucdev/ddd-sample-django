import uuid
from datetime import date

from lending.domain.events import BookLoaned, BookReturned, LoanOverdue
from lending.domain.exceptions import AlreadyReturned, RenewalNotAllowed
from lending.domain.value_objects import STANDARD_LOAN_PERIOD, LoanPeriod
from shared.domain.entity import Entity


class Loan(Entity):
    """貸出。集約ルート。

    「会員が蔵書(個体)1 点を借りている状態」を表す(lending/CONTEXT.md 参照)。
    貸出は蔵書(copy)単位であり、書誌(title)単位ではない。
    """

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
    def start(
        cls,
        *,
        member_id: uuid.UUID,
        copy_id: uuid.UUID,
        loaned_at: date,
        loan_period: LoanPeriod = STANDARD_LOAN_PERIOD,
    ) -> "Loan":
        """新規貸出を開始する。ID はここで採番する(DB の自動採番に頼ると、保存前のエンティティが ID を持てない)。

        `loan_period` は会員ランクに応じた貸出期間(lending.domain.value_objects.loan_terms_for_rank
        参照)。呼び出し側(application 層)が会員ランクから引き当てて渡す。
        """
        loan = cls(
            loan_id=uuid.uuid4(),
            member_id=member_id,
            copy_id=copy_id,
            loaned_at=loaned_at,
            due_date=loan_period.due_date_from(loaned_at),
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

    def renew(
        self,
        *,
        today: date,
        has_reservation: bool,
        loan_period: LoanPeriod = STANDARD_LOAN_PERIOD,
    ) -> None:
        """返却期限を延長する。1 回まで、延滞中、または対象書誌に予約がある場合は延長できない。

        `has_reservation`(対象書誌に予約があるか)は reservation モジュールの公開 API を
        呼び出し側(application 層)が照会し、判定結果だけを渡してもらう。domain 層は
        他モジュールに依存しない。`loan_period` も同様に、会員ランクに応じた貸出期間を
        呼び出し側が引き当てて渡す。
        """
        if self.is_returned:
            raise AlreadyReturned(self.id)
        if self.renewal_count >= 1:
            raise RenewalNotAllowed(self.id, "loan has already been renewed once")
        if self.is_overdue(today):
            raise RenewalNotAllowed(self.id, "loan is overdue")
        if has_reservation:
            raise RenewalNotAllowed(self.id, "title has a pending reservation")
        self.renewal_count += 1
        self.due_date = loan_period.due_date_from(today)

    def mark_overdue(self) -> None:
        """延滞を確定させ `LoanOverdue` イベントを発行する。

        `detect_overdue` コマンドから複数回呼ばれても再発行しないよう、
        `overdue_notified` フラグで冪等にしている。
        """
        if self.is_returned:
            raise AlreadyReturned(self.id)
        if self.overdue_notified:
            return
        self.overdue_notified = True
        self.record_event(
            LoanOverdue(loan_id=self.id, member_id=self.member_id, copy_id=self.copy_id)
        )
