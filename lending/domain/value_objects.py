from dataclasses import dataclass
from datetime import date, timedelta

from shared.domain.value_object import ValueObject

STANDARD_LOAN_DAYS = 14


@dataclass(frozen=True)
class LoanPeriod(ValueObject):
    """貸出期間。値オブジェクト。値(日数)が同じなら同じものとして扱う。"""

    days: int = STANDARD_LOAN_DAYS

    def due_date_from(self, start: date) -> date:
        return start + timedelta(days=self.days)


# 標準の貸出期間(14日)。貸出開始・延長のどちらでもこの期間を使う。
STANDARD_LOAN_PERIOD = LoanPeriod()
