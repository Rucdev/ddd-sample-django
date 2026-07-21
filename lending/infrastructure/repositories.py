import uuid

from lending.domain.entities import Loan
from lending.infrastructure.models import LoanModel


class DjangoLoanRepository:
    def save(self, loan: Loan) -> None:
        LoanModel.objects.update_or_create(
            id=loan.id,
            defaults={
                "member_id": loan.member_id,
                "copy_id": loan.copy_id,
                "loaned_at": loan.loaned_at,
                "due_date": loan.due_date,
                "returned_at": loan.returned_at,
                "renewal_count": loan.renewal_count,
                "overdue_notified": loan.overdue_notified,
            },
        )

    def find_by_id(self, loan_id: uuid.UUID) -> Loan | None:
        model = LoanModel.objects.filter(id=loan_id).first()
        return self._to_entity(model) if model else None

    def count_active_by_member(self, member_id: uuid.UUID) -> int:
        return LoanModel.objects.filter(member_id=member_id, returned_at__isnull=True).count()

    def count_overdue_by_member(self, member_id: uuid.UUID) -> int:
        # overdue_notified is the persisted marker set by the detect_overdue command;
        # this counts loans that were overdue and are still unreturned.
        return LoanModel.objects.filter(
            member_id=member_id, returned_at__isnull=True, overdue_notified=True
        ).count()

    def find_active_by_copy(self, copy_id: uuid.UUID) -> Loan | None:
        model = LoanModel.objects.filter(copy_id=copy_id, returned_at__isnull=True).first()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_entity(model: LoanModel) -> Loan:
        return Loan(
            loan_id=model.id,
            member_id=model.member_id,
            copy_id=model.copy_id,
            loaned_at=model.loaned_at,
            due_date=model.due_date,
            returned_at=model.returned_at,
            renewal_count=model.renewal_count,
            overdue_notified=model.overdue_notified,
        )
