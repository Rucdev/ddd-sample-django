import uuid
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from lending.domain.entities import Loan
from lending.domain.events import LoanOverdue
from lending.infrastructure.repositories import DjangoLoanRepository
from shared.infrastructure import event_bus


class DetectOverdueCommandTests(TestCase):
    def setUp(self) -> None:
        event_bus.clear_subscribers()
        self.addCleanup(event_bus.clear_subscribers)

        self.repository = DjangoLoanRepository()

    def _make_loan(self, *, loaned_at: date) -> Loan:
        loan = Loan.start(member_id=uuid.uuid4(), copy_id=uuid.uuid4(), loaned_at=loaned_at)
        loan.collect_events()
        self.repository.save(loan)
        return loan

    def test_marks_overdue_loan_and_publishes_event(self) -> None:
        loan = self._make_loan(loaned_at=date.today() - timedelta(days=30))
        received = []
        event_bus.subscribe(LoanOverdue, received.append)

        call_command("detect_overdue")

        updated = self.repository.find_by_id(loan.id)
        self.assertTrue(updated.overdue_notified)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].loan_id, loan.id)

    def test_leaves_loan_not_yet_due_untouched(self) -> None:
        loan = self._make_loan(loaned_at=date.today())

        call_command("detect_overdue")

        updated = self.repository.find_by_id(loan.id)
        self.assertFalse(updated.overdue_notified)

    def test_leaves_returned_loan_untouched_even_if_overdue(self) -> None:
        loan = self._make_loan(loaned_at=date.today() - timedelta(days=30))
        loan.return_book(today=date.today())
        loan.collect_events()
        self.repository.save(loan)

        call_command("detect_overdue")

        updated = self.repository.find_by_id(loan.id)
        self.assertFalse(updated.overdue_notified)

    def test_is_idempotent(self) -> None:
        self._make_loan(loaned_at=date.today() - timedelta(days=30))
        received = []
        event_bus.subscribe(LoanOverdue, received.append)

        call_command("detect_overdue")
        call_command("detect_overdue")

        self.assertEqual(len(received), 1)
