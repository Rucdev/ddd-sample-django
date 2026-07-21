from dataclasses import dataclass
from datetime import date, timedelta

from shared.domain.value_object import ValueObject

STANDARD_LOAN_DAYS = 14


@dataclass(frozen=True)
class LoanPeriod(ValueObject):
    days: int = STANDARD_LOAN_DAYS

    def due_date_from(self, start: date) -> date:
        return start + timedelta(days=self.days)


STANDARD_LOAN_PERIOD = LoanPeriod()
