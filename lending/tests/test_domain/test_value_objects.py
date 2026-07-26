from datetime import date
from unittest import TestCase

from lending.domain.value_objects import (
    EXTENDED_LOAN_DAYS,
    STANDARD_LOAN_DAYS,
    STANDARD_LOAN_PERIOD,
    LoanPeriod,
    loan_terms_for_rank,
)


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


class LoanTermsForRankTests(TestCase):
    def test_regular_rank_allows_5_books_for_14_days(self) -> None:
        terms = loan_terms_for_rank("REGULAR")

        self.assertEqual(terms.loan_limit, 5)
        self.assertEqual(terms.loan_period, STANDARD_LOAN_PERIOD)

    def test_silver_rank_allows_5_books_for_21_days(self) -> None:
        terms = loan_terms_for_rank("SILVER")

        self.assertEqual(terms.loan_limit, 5)
        self.assertEqual(terms.loan_period.days, EXTENDED_LOAN_DAYS)

    def test_gold_rank_allows_10_books_for_21_days(self) -> None:
        terms = loan_terms_for_rank("GOLD")

        self.assertEqual(terms.loan_limit, 10)
        self.assertEqual(terms.loan_period.days, EXTENDED_LOAN_DAYS)

    def test_unknown_rank_falls_back_to_regular(self) -> None:
        self.assertEqual(loan_terms_for_rank("UNKNOWN"), loan_terms_for_rank("REGULAR"))

    def test_none_rank_falls_back_to_regular(self) -> None:
        self.assertEqual(loan_terms_for_rank(None), loan_terms_for_rank("REGULAR"))
