import uuid
from datetime import date, timedelta
from unittest import TestCase

from lending.domain.entities import Loan
from lending.domain.events import BookLoaned, BookReturned, LoanOverdue
from lending.domain.exceptions import AlreadyReturned, RenewalNotAllowed
from lending.domain.value_objects import STANDARD_LOAN_DAYS


def _make_loan() -> Loan:
    return Loan.start(member_id=uuid.uuid4(), copy_id=uuid.uuid4(), loaned_at=date(2026, 1, 1))


class LoanStartTests(TestCase):
    def test_start_sets_due_date_14_days_out(self) -> None:
        loaned_at = date(2026, 1, 1)

        loan = Loan.start(member_id=uuid.uuid4(), copy_id=uuid.uuid4(), loaned_at=loaned_at)

        self.assertEqual(loan.due_date, loaned_at + timedelta(days=STANDARD_LOAN_DAYS))

    def test_start_records_book_loaned_event(self) -> None:
        member_id, copy_id = uuid.uuid4(), uuid.uuid4()

        loan = Loan.start(member_id=member_id, copy_id=copy_id, loaned_at=date(2026, 1, 1))
        events = loan.collect_events()

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, BookLoaned)
        self.assertEqual(event.loan_id, loan.id)
        self.assertEqual(event.member_id, member_id)
        self.assertEqual(event.copy_id, copy_id)


class LoanReturnTests(TestCase):
    def test_return_book_sets_returned_at(self) -> None:
        loan = _make_loan()

        loan.return_book(today=date(2026, 1, 10))

        self.assertEqual(loan.returned_at, date(2026, 1, 10))

    def test_return_book_records_book_returned_event(self) -> None:
        loan = _make_loan()
        loan.collect_events()

        loan.return_book(today=date(2026, 1, 10))
        events = loan.collect_events()

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], BookReturned)

    def test_return_book_twice_raises(self) -> None:
        loan = _make_loan()
        loan.return_book(today=date(2026, 1, 10))

        with self.assertRaises(AlreadyReturned):
            loan.return_book(today=date(2026, 1, 11))


class LoanRenewTests(TestCase):
    def test_renew_extends_due_date_and_increments_count(self) -> None:
        loan = _make_loan()
        original_due = loan.due_date

        loan.renew(today=date(2026, 1, 10), has_reservation=False)

        self.assertGreater(loan.due_date, original_due)
        self.assertEqual(loan.renewal_count, 1)

    def test_renew_twice_raises(self) -> None:
        loan = _make_loan()
        loan.renew(today=date(2026, 1, 10), has_reservation=False)

        with self.assertRaises(RenewalNotAllowed):
            loan.renew(today=date(2026, 1, 12), has_reservation=False)

    def test_renew_while_overdue_raises(self) -> None:
        loan = _make_loan()

        with self.assertRaises(RenewalNotAllowed):
            loan.renew(today=loan.due_date + timedelta(days=1), has_reservation=False)

    def test_renew_with_pending_reservation_raises(self) -> None:
        loan = _make_loan()

        with self.assertRaises(RenewalNotAllowed):
            loan.renew(today=date(2026, 1, 10), has_reservation=True)

    def test_renew_after_return_raises(self) -> None:
        loan = _make_loan()
        loan.return_book(today=date(2026, 1, 5))

        with self.assertRaises(AlreadyReturned):
            loan.renew(today=date(2026, 1, 10), has_reservation=False)


class LoanOverdueTests(TestCase):
    def test_is_overdue_false_on_due_date(self) -> None:
        loan = _make_loan()

        self.assertFalse(loan.is_overdue(loan.due_date))

    def test_is_overdue_true_after_due_date(self) -> None:
        loan = _make_loan()

        self.assertTrue(loan.is_overdue(loan.due_date + timedelta(days=1)))

    def test_mark_overdue_records_event_only_once(self) -> None:
        loan = _make_loan()
        loan.collect_events()

        loan.mark_overdue()
        events_first = loan.collect_events()
        loan.mark_overdue()
        events_second = loan.collect_events()

        self.assertEqual(len(events_first), 1)
        self.assertIsInstance(events_first[0], LoanOverdue)
        self.assertEqual(events_second, [])

    def test_mark_overdue_after_return_raises(self) -> None:
        loan = _make_loan()
        loan.return_book(today=date(2026, 1, 5))

        with self.assertRaises(AlreadyReturned):
            loan.mark_overdue()
