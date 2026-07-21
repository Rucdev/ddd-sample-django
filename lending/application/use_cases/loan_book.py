from datetime import date

from django.db import transaction

from catalog.public import get_copy
from lending.application import reservation_gateway
from lending.application.dto import LoanBookInput, LoanDTO
from lending.domain.entities import Loan
from lending.domain.exceptions import CopyNotLoanable, MemberNotLoanable
from lending.domain.repositories import LoanRepository
from lending.domain.services import LoanPolicy
from members.public import get_member
from shared.infrastructure.event_bus import publish


class LoanBookUseCase:
    def __init__(self, loan_repository: LoanRepository) -> None:
        self._loan_repository = loan_repository
        self._policy = LoanPolicy(loan_repository)

    def execute(self, data: LoanBookInput, *, today: date | None = None) -> LoanDTO:
        today = today or date.today()

        with transaction.atomic():
            member = get_member(data.member_id)
            if member is None or not member.is_active:
                raise MemberNotLoanable(data.member_id)

            copy = get_copy(data.copy_id)
            if copy is None or not copy.is_active:
                raise CopyNotLoanable(data.copy_id, "copy is not in the collection")

            if self._loan_repository.find_active_by_copy(data.copy_id) is not None:
                raise CopyNotLoanable(data.copy_id, "copy is already on loan")

            holder_id = reservation_gateway.get_holder_for_copy(data.copy_id)
            if holder_id is not None and holder_id != data.member_id:
                raise CopyNotLoanable(data.copy_id, "copy is held for another member")

            self._policy.ensure_member_can_borrow(data.member_id)

            loan = Loan.start(member_id=data.member_id, copy_id=data.copy_id, loaned_at=today)
            self._loan_repository.save(loan)
            publish(loan.collect_events())

        return LoanDTO.from_entity(loan)
