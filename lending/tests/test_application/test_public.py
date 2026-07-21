import uuid
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from lending import public
from lending.domain.entities import Loan
from lending.infrastructure.repositories import DjangoLoanRepository
from shared.infrastructure import event_bus


class CountOverdueLoansTests(TestCase):
    def setUp(self) -> None:
        event_bus.clear_subscribers()
        self.addCleanup(event_bus.clear_subscribers)

        self.member_id = uuid.uuid4()
        self.repository = DjangoLoanRepository()

    def test_returns_zero_when_no_loans(self) -> None:
        self.assertEqual(public.count_overdue_loans(self.member_id), 0)

    def test_counts_unreturned_overdue_loans_after_detection(self) -> None:
        loan = Loan.start(
            member_id=self.member_id,
            copy_id=uuid.uuid4(),
            loaned_at=date.today() - timedelta(days=30),
        )
        loan.collect_events()
        self.repository.save(loan)
        call_command("detect_overdue")

        self.assertEqual(public.count_overdue_loans(self.member_id), 1)

    def test_excludes_returned_loans(self) -> None:
        loan = Loan.start(
            member_id=self.member_id,
            copy_id=uuid.uuid4(),
            loaned_at=date.today() - timedelta(days=30),
        )
        loan.collect_events()
        self.repository.save(loan)
        call_command("detect_overdue")

        loan = self.repository.find_by_id(loan.id)
        loan.return_book(today=date.today())
        self.repository.save(loan)

        self.assertEqual(public.count_overdue_loans(self.member_id), 0)
