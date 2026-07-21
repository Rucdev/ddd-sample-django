from datetime import date
from unittest import TestCase

from lending.domain.value_objects import STANDARD_LOAN_DAYS, LoanPeriod


class LoanPeriodTests(TestCase):
    def test_default_period_is_14_days(self) -> None:
        self.assertEqual(LoanPeriod().days, STANDARD_LOAN_DAYS)

    def test_due_date_from_adds_period_days(self) -> None:
        period = LoanPeriod(days=7)

        self.assertEqual(period.due_date_from(date(2026, 1, 1)), date(2026, 1, 8))

    def test_is_immutable(self) -> None:
        period = LoanPeriod()

        with self.assertRaises(AttributeError):
            period.days = 30  # type: ignore[misc]
