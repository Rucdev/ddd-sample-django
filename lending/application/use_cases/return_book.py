from datetime import date

from django.db import transaction

from lending.application.dto import LoanDTO, ReturnBookInput
from lending.domain.exceptions import LoanNotFound
from lending.domain.repositories import LoanRepository
from shared.infrastructure.event_bus import publish


class ReturnBookUseCase:
    """返却ユースケース。`BookReturned` イベントの発行が、reservation モジュールの
    取置作成・members モジュールの貸出停止解除のきっかけになる。
    """

    def __init__(self, loan_repository: LoanRepository) -> None:
        self._loan_repository = loan_repository

    def execute(self, data: ReturnBookInput, *, today: date | None = None) -> LoanDTO:
        today = today or date.today()

        with transaction.atomic():
            loan = self._loan_repository.find_by_id(data.loan_id)
            if loan is None:
                raise LoanNotFound(data.loan_id)

            loan.return_book(today=today)
            self._loan_repository.save(loan)
            publish(loan.collect_events())

        return LoanDTO.from_entity(loan)
