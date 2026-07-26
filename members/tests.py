import uuid
from datetime import date, timedelta

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog.models import Copy, Title
from lending.application.dto import LoanBookInput, ReturnBookInput
from lending.application.use_cases.loan_book import LoanBookUseCase
from lending.application.use_cases.return_book import ReturnBookUseCase
from lending.domain.entities import Loan
from lending.domain.events import BookReturned, LoanOverdue
from lending.infrastructure.repositories import DjangoLoanRepository
from members import public
from members.event_handlers import handle_book_returned, handle_loan_overdue
from members.models import Member


class MemberModelTests(TestCase):
    def test_email_must_be_unique(self) -> None:
        Member.objects.create(name="Alice", email="alice@example.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Member.objects.create(name="Alice Duplicate", email="alice@example.com")

    def test_default_status_is_active(self) -> None:
        member = Member.objects.create(name="Alice", email="alice@example.com")

        self.assertEqual(member.status, Member.Status.ACTIVE)

    def test_default_rank_is_regular(self) -> None:
        member = Member.objects.create(name="Alice", email="alice@example.com")

        self.assertEqual(member.rank, Member.Rank.REGULAR)


class PublicApiTests(TestCase):
    def setUp(self) -> None:
        self.member = Member.objects.create(name="Alice", email="alice@example.com")

    def test_get_member_returns_dto(self) -> None:
        dto = public.get_member(self.member.id)

        assert dto is not None
        self.assertEqual(dto.name, "Alice")
        self.assertTrue(dto.is_active)
        self.assertEqual(dto.rank, Member.Rank.REGULAR)

    def test_get_member_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_member(uuid.uuid4()))

    def test_get_member_returns_dto_with_member_rank(self) -> None:
        gold_member = Member.objects.create(
            name="Bob", email="bob@example.com", rank=Member.Rank.GOLD
        )

        dto = public.get_member(gold_member.id)

        assert dto is not None
        self.assertEqual(dto.rank, Member.Rank.GOLD)

    def test_suspend_member_flips_status(self) -> None:
        public.suspend_member(self.member.id)

        dto = public.get_member(self.member.id)
        assert dto is not None
        self.assertFalse(dto.is_active)

    def test_reinstate_member_flips_status_back(self) -> None:
        public.suspend_member(self.member.id)
        public.reinstate_member(self.member.id)

        dto = public.get_member(self.member.id)
        assert dto is not None
        self.assertTrue(dto.is_active)


class HandleLoanOverdueTests(TestCase):
    def test_suspends_the_member(self) -> None:
        member = Member.objects.create(name="Alice", email="alice@example.com")
        event = LoanOverdue(loan_id=uuid.uuid4(), member_id=member.id, copy_id=uuid.uuid4())

        handle_loan_overdue(event)

        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.SUSPENDED)


class HandleBookReturnedTests(TestCase):
    def test_reinstates_member_when_no_overdue_loans_remain(self) -> None:
        member = Member.objects.create(
            name="Alice", email="alice@example.com", status=Member.Status.SUSPENDED
        )
        event = BookReturned(
            loan_id=uuid.uuid4(),
            member_id=member.id,
            copy_id=uuid.uuid4(),
            returned_at=date.today(),
        )

        handle_book_returned(event)

        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.ACTIVE)

    def test_leaves_member_suspended_when_other_overdue_loans_remain(self) -> None:
        member = Member.objects.create(
            name="Alice", email="alice@example.com", status=Member.Status.SUSPENDED
        )
        repository = DjangoLoanRepository()
        other_loan = Loan.start(
            member_id=member.id,
            copy_id=uuid.uuid4(),
            loaned_at=date.today() - timedelta(days=30),
        )
        other_loan.collect_events()
        repository.save(other_loan)
        other_loan.mark_overdue()
        other_loan.collect_events()
        repository.save(other_loan)

        event = BookReturned(
            loan_id=uuid.uuid4(),
            member_id=member.id,
            copy_id=uuid.uuid4(),
            returned_at=date.today(),
        )
        handle_book_returned(event)

        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.SUSPENDED)


class MemberSuspensionIntegrationTests(TestCase):
    """Exercises the real ready()-installed subscriptions end to end, with no mocking."""

    def test_overdue_loan_suspends_member_and_full_return_reinstates(self) -> None:
        member = Member.objects.create(name="Alice", email="alice@example.com")
        title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        copy = Copy.objects.create(title=title, copy_number=1)

        LoanBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            LoanBookInput(member_id=member.id, copy_id=copy.id),
            today=date.today() - timedelta(days=30),
        )

        call_command("detect_overdue")

        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.SUSPENDED)

        loan = DjangoLoanRepository().find_active_by_copy(copy.id)
        ReturnBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            ReturnBookInput(loan_id=loan.id), today=date.today()
        )

        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.ACTIVE)
