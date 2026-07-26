from datetime import date

from django.db import transaction

from catalog.public import get_copy
from lending.application.dto import LoanDTO, RenewLoanInput
from lending.domain.exceptions import LoanNotFound
from lending.domain.repositories import LoanRepository
from lending.domain.value_objects import loan_terms_for_rank
from members.public import get_member
from reservation.public import has_reservation
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

            # 対象書誌に予約があるかは reservation モジュールに照会し、判定結果(bool)
            # だけを domain 層(Loan.renew)に渡す。domain 層は他モジュールを知らない。
            copy = get_copy(loan.copy_id)
            title_has_reservation = has_reservation(copy.title_id) if copy else False

            # 延長後の貸出期間も会員ランクに応じて変わる(members.public.MemberDTO.rank)。
            member = get_member(loan.member_id)
            loan_terms = loan_terms_for_rank(member.rank if member else None)

            loan.renew(
                today=today,
                has_reservation=title_has_reservation,
                loan_period=loan_terms.loan_period,
            )
            self._loan_repository.save(loan)
            publish(loan.collect_events())

        return LoanDTO.from_entity(loan)
