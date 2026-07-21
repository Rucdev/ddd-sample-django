from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from lending.infrastructure.models import LoanModel
from lending.infrastructure.repositories import DjangoLoanRepository
from shared.infrastructure.event_bus import publish


class Command(BaseCommand):
    help = "Mark unreturned loans past their due date as overdue and publish LoanOverdue events."

    def handle(self, *args, **options):
        today = date.today()
        repository = DjangoLoanRepository()
        overdue_ids = LoanModel.objects.filter(
            returned_at__isnull=True,
            due_date__lt=today,
            overdue_notified=False,
        ).values_list("id", flat=True)

        count = 0
        for loan_id in overdue_ids:
            with transaction.atomic():
                loan = repository.find_by_id(loan_id)
                if loan is None or loan.overdue_notified:
                    continue
                loan.mark_overdue()
                repository.save(loan)
                publish(loan.collect_events())
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Marked {count} loan(s) as overdue."))
