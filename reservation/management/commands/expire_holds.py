from datetime import date

from django.core.management.base import BaseCommand

from reservation.application.use_cases.expire_holds import ExpireHoldsUseCase
from reservation.infrastructure.repositories import DjangoReservationQueueRepository


class Command(BaseCommand):
    help = "Expire holds past their expiry date and promote the next reservation, if any."

    def handle(self, *args, **options):
        today = date.today()
        repository = DjangoReservationQueueRepository()
        use_case = ExpireHoldsUseCase(repository=repository)

        title_ids = repository.titles_with_expired_holds(today)
        for title_id in title_ids:
            use_case.execute(title_id, today=today)

        self.stdout.write(
            self.style.SUCCESS(f"Processed {len(title_ids)} title(s) with expired holds.")
        )
