import uuid
from datetime import date

from django.test import TestCase

from catalog.models import Copy, Title
from lending.application.dto import RenewLoanInput
from lending.application.use_cases.renew_loan import RenewLoanUseCase
from lending.domain.entities import Loan
from lending.domain.exceptions import LoanNotFound, RenewalNotAllowed
from lending.tests.test_application.fakes import FakeLoanRepository
from reservation.infrastructure.models import ReservationModel


class RenewLoanUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

        self.repository = FakeLoanRepository()
        self.use_case = RenewLoanUseCase(loan_repository=self.repository)

        self.loan = Loan.start(
            member_id=uuid.uuid4(), copy_id=self.copy.id, loaned_at=date(2026, 1, 1)
        )
        self.loan.collect_events()
        self.repository.save(self.loan)

    def test_extends_due_date(self) -> None:
        original_due = self.loan.due_date

        result = self.use_case.execute(
            RenewLoanInput(loan_id=self.loan.id), today=date(2026, 1, 10)
        )

        self.assertGreater(result.due_date, original_due)
        self.assertEqual(result.renewal_count, 1)

    def test_raises_for_unknown_loan(self) -> None:
        with self.assertRaises(LoanNotFound):
            self.use_case.execute(RenewLoanInput(loan_id=uuid.uuid4()), today=date(2026, 1, 10))

    def test_raises_when_title_has_pending_reservation(self) -> None:
        ReservationModel.objects.create(
            title_id=self.title.id, member_id=uuid.uuid4(), requested_at=date(2026, 1, 1)
        )

        with self.assertRaises(RenewalNotAllowed):
            self.use_case.execute(RenewLoanInput(loan_id=self.loan.id), today=date(2026, 1, 10))

    def test_raises_when_already_renewed(self) -> None:
        self.use_case.execute(RenewLoanInput(loan_id=self.loan.id), today=date(2026, 1, 10))

        with self.assertRaises(RenewalNotAllowed):
            self.use_case.execute(RenewLoanInput(loan_id=self.loan.id), today=date(2026, 1, 12))
