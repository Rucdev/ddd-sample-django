"""Verifies the real production wiring: lending's BookReturned event, published through
the shared event bus, reaches reservation's ready()-installed subscription and results
in a hold — without any test-local subscribe/mock standing in for it.
"""

from datetime import date, timedelta

from django.test import TestCase

from catalog.models import Copy, Title
from lending.application.dto import LoanBookInput, ReturnBookInput
from lending.application.use_cases.loan_book import LoanBookUseCase
from lending.application.use_cases.return_book import ReturnBookUseCase
from lending.infrastructure.repositories import DjangoLoanRepository
from members.models import Member
from reservation import public
from reservation.application.dto import ReserveTitleInput
from reservation.application.use_cases.reserve_title import ReserveTitleUseCase
from reservation.domain.value_objects import HOLD_PERIOD_DAYS
from reservation.infrastructure.repositories import DjangoReservationQueueRepository


class BookReturnedTriggersHoldIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.borrower = Member.objects.create(name="Alice", email="alice@example.com")
        self.waiting_member = Member.objects.create(name="Bob", email="bob@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

    def test_returning_a_book_creates_a_hold_for_the_waiting_member(self) -> None:
        LoanBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            LoanBookInput(member_id=self.borrower.id, copy_id=self.copy.id),
            today=date(2026, 1, 1),
        )
        ReserveTitleUseCase(repository=DjangoReservationQueueRepository()).execute(
            ReserveTitleInput(member_id=self.waiting_member.id, title_id=self.title.id),
            today=date(2026, 1, 2),
        )

        ReturnBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            ReturnBookInput(loan_id=DjangoLoanRepository().find_active_by_copy(self.copy.id).id),
            today=date(2026, 1, 10),
        )

        hold = public.get_active_hold_for_copy(self.copy.id)
        self.assertIsNotNone(hold)
        self.assertEqual(hold.member_id, self.waiting_member.id)
        self.assertEqual(hold.expires_at, date(2026, 1, 10) + timedelta(days=HOLD_PERIOD_DAYS))

    def test_returning_a_book_with_no_reservation_creates_no_hold(self) -> None:
        LoanBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            LoanBookInput(member_id=self.borrower.id, copy_id=self.copy.id),
            today=date(2026, 1, 1),
        )

        ReturnBookUseCase(loan_repository=DjangoLoanRepository()).execute(
            ReturnBookInput(loan_id=DjangoLoanRepository().find_active_by_copy(self.copy.id).id),
            today=date(2026, 1, 10),
        )

        self.assertIsNone(public.get_active_hold_for_copy(self.copy.id))
