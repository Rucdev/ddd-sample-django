from datetime import date

from django.db import transaction

from catalog.public import get_copy
from lending.application import reservation_gateway
from lending.application.dto import LoanDTO, RenewLoanInput
from lending.domain.exceptions import LoanNotFound
from lending.domain.repositories import LoanRepository
from shared.infrastructure.event_bus import publish


class RenewLoanUseCase:
    def __init__(self, loan_repository: LoanRepository) -> None:
        self._loan_repository = loan_repository

    def execute(self, data: RenewLoanInput, *, today: date | None = None) -> LoanDTO:
        today = today or date.today()

        with transaction.atomic():
            loan = self._loan_repository.find_by_id(data.loan_id)
            if loan is None:
                raise LoanNotFound(data.loan_id)

            copy = get_copy(loan.copy_id)
            has_reservation = reservation_gateway.has_reservation(copy.title_id) if copy else False

            loan.renew(today=today, has_reservation=has_reservation)
            self._loan_repository.save(loan)
            publish(loan.collect_events())

        return LoanDTO.from_entity(loan)
