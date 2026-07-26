from datetime import date

from django.db import transaction

from catalog.public import get_copy
from lending.application.dto import LoanBookInput, LoanDTO
from lending.domain.entities import Loan
from lending.domain.exceptions import CopyNotLoanable, MemberNotLoanable
from lending.domain.repositories import LoanRepository
from lending.domain.services import LoanPolicy
from lending.domain.value_objects import loan_terms_for_rank
from members.public import get_member
from reservation.public import get_active_hold_for_copy
from shared.infrastructure.event_bus import publish


class LoanBookUseCase:
    """貸出ユースケース。会員・蔵書のチェックはここ(application 層)で行い、
    貸出そのものの成立判定(上限冊数など)は domain 層(Loan / LoanPolicy)に委ねる。

    リポジトリは呼び出し側(presentation 層)がコンストラクタに注入する。DI コンテナは
    使わず、view/API で具象クラスを直接組み立てる方針(directory-structure.md 参照)。
    """

    def __init__(self, loan_repository: LoanRepository) -> None:
        self._loan_repository = loan_repository

    def execute(self, data: LoanBookInput, *, today: date | None = None) -> LoanDTO:
        today = today or date.today()

        with transaction.atomic():
            # 会員・蔵書の有効性チェックは、それぞれの公開 API(DTO)を通じて行う。
            # ORM モデルやエンティティを直接 import しない。
            member = get_member(data.member_id)
            if member is None or not member.is_active:
                raise MemberNotLoanable(data.member_id)

            copy = get_copy(data.copy_id)
            if copy is None or not copy.is_active:
                raise CopyNotLoanable(data.copy_id, "copy is not in the collection")

            if self._loan_repository.find_active_by_copy(data.copy_id) is not None:
                raise CopyNotLoanable(data.copy_id, "copy is already on loan")

            # 取置中の蔵書は、取置対象の会員以外には貸し出せない(reservation モジュールへの照会)。
            hold = get_active_hold_for_copy(data.copy_id)
            if hold is not None and hold.member_id != data.member_id:
                raise CopyNotLoanable(data.copy_id, "copy is held for another member")

            # 貸出上限・貸出期間は会員ランクに応じて変わる(members.public.MemberDTO.rank)。
            loan_terms = loan_terms_for_rank(member.rank)
            policy = LoanPolicy(self._loan_repository, limit=loan_terms.loan_limit)
            policy.ensure_member_can_borrow(data.member_id)

            loan = Loan.start(
                member_id=data.member_id,
                copy_id=data.copy_id,
                loaned_at=today,
                loan_period=loan_terms.loan_period,
            )
            self._loan_repository.save(loan)
            # 集約が保持していたイベントを取り出して発行する。同一トランザクション内で
            # 同期的にハンドラが呼ばれるため、ハンドラが失敗すれば貸出自体もロールバックされる。
            publish(loan.collect_events())

        return LoanDTO.from_entity(loan)
