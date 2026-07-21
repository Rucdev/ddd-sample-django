import uuid
from datetime import date

from django.test import TestCase

from lending.application.dto import ReturnBookInput
from lending.application.use_cases.return_book import ReturnBookUseCase
from lending.domain.entities import Loan
from lending.domain.events import BookReturned
from lending.domain.exceptions import AlreadyReturned, LoanNotFound
from lending.tests.test_application.fakes import FakeLoanRepository
from shared.infrastructure import event_bus


class ReturnBookUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.repository = FakeLoanRepository()
        self.use_case = ReturnBookUseCase(loan_repository=self.repository)

        self.loan = Loan.start(
            member_id=uuid.uuid4(), copy_id=uuid.uuid4(), loaned_at=date(2026, 1, 1)
        )
        self.loan.collect_events()
        self.repository.save(self.loan)

    def test_returns_loan(self) -> None:
        result = self.use_case.execute(
            ReturnBookInput(loan_id=self.loan.id), today=date(2026, 1, 10)
        )

        self.assertEqual(result.returned_at, date(2026, 1, 10))

    def test_publishes_book_returned_event(self) -> None:
        received = []
        event_bus.subscribe(BookReturned, received.append)
        self.addCleanup(event_bus.unsubscribe, BookReturned, received.append)

        self.use_case.execute(ReturnBookInput(loan_id=self.loan.id), today=date(2026, 1, 10))

        self.assertEqual(len(received), 1)

    def test_raises_for_unknown_loan(self) -> None:
        with self.assertRaises(LoanNotFound):
            self.use_case.execute(ReturnBookInput(loan_id=uuid.uuid4()), today=date(2026, 1, 10))

    def test_raises_when_already_returned(self) -> None:
        self.use_case.execute(ReturnBookInput(loan_id=self.loan.id), today=date(2026, 1, 10))

        with self.assertRaises(AlreadyReturned):
            self.use_case.execute(ReturnBookInput(loan_id=self.loan.id), today=date(2026, 1, 11))
