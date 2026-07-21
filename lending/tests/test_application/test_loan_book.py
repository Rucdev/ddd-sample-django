import uuid
from datetime import date

from django.test import TestCase

from catalog.models import Copy, Title
from lending.application.dto import LoanBookInput
from lending.application.use_cases.loan_book import LoanBookUseCase
from lending.domain.entities import Loan
from lending.domain.events import BookLoaned
from lending.domain.exceptions import CopyNotLoanable, LoanLimitExceeded, MemberNotLoanable
from lending.tests.test_application.fakes import FakeLoanRepository
from members.models import Member
from reservation.infrastructure.models import HoldModel
from shared.infrastructure import event_bus


class LoanBookUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

        self.repository = FakeLoanRepository()
        self.use_case = LoanBookUseCase(loan_repository=self.repository)

    def test_loans_book_to_active_member(self) -> None:
        result = self.use_case.execute(
            LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
            today=date(2026, 1, 1),
        )

        self.assertEqual(result.member_id, self.member.id)
        self.assertEqual(result.copy_id, self.copy.id)
        self.assertEqual(result.due_date, date(2026, 1, 15))
        self.assertIsNotNone(self.repository.find_by_id(result.id))

    def test_publishes_book_loaned_event(self) -> None:
        received = []
        event_bus.subscribe(BookLoaned, received.append)
        self.addCleanup(event_bus.unsubscribe, BookLoaned, received.append)

        self.use_case.execute(
            LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
            today=date(2026, 1, 1),
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].member_id, self.member.id)

    def test_rejects_unknown_member(self) -> None:
        with self.assertRaises(MemberNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=uuid.uuid4(), copy_id=self.copy.id),
                today=date(2026, 1, 1),
            )

    def test_rejects_suspended_member(self) -> None:
        self.member.status = Member.Status.SUSPENDED
        self.member.save()

        with self.assertRaises(MemberNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
                today=date(2026, 1, 1),
            )

    def test_rejects_unknown_copy(self) -> None:
        with self.assertRaises(CopyNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=uuid.uuid4()),
                today=date(2026, 1, 1),
            )

    def test_rejects_withdrawn_copy(self) -> None:
        self.copy.status = Copy.Status.WITHDRAWN
        self.copy.save()

        with self.assertRaises(CopyNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
                today=date(2026, 1, 1),
            )

    def test_rejects_copy_already_on_loan(self) -> None:
        existing = Loan.start(
            member_id=uuid.uuid4(), copy_id=self.copy.id, loaned_at=date(2026, 1, 1)
        )
        self.repository.save(existing)

        with self.assertRaises(CopyNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
                today=date(2026, 1, 2),
            )

    def test_rejects_copy_held_for_another_member(self) -> None:
        HoldModel.objects.create(
            title_id=self.title.id,
            copy_id=self.copy.id,
            member_id=uuid.uuid4(),
            expires_at=date(2026, 1, 8),
        )

        with self.assertRaises(CopyNotLoanable):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
                today=date(2026, 1, 1),
            )

    def test_allows_copy_held_for_the_borrowing_member(self) -> None:
        HoldModel.objects.create(
            title_id=self.title.id,
            copy_id=self.copy.id,
            member_id=self.member.id,
            expires_at=date(2026, 1, 8),
        )

        result = self.use_case.execute(
            LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
            today=date(2026, 1, 1),
        )

        self.assertEqual(result.member_id, self.member.id)

    def test_rejects_when_loan_limit_reached(self) -> None:
        for _ in range(5):
            loan = Loan.start(
                member_id=self.member.id, copy_id=uuid.uuid4(), loaned_at=date(2026, 1, 1)
            )
            self.repository.save(loan)

        with self.assertRaises(LoanLimitExceeded):
            self.use_case.execute(
                LoanBookInput(member_id=self.member.id, copy_id=self.copy.id),
                today=date(2026, 1, 2),
            )
