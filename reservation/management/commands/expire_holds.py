from datetime import date

from django.core.management.base import BaseCommand

from reservation.application.use_cases.expire_holds import ExpireHoldsUseCase
from reservation.infrastructure.repositories import DjangoReservationQueueRepository


class Command(BaseCommand):
    """期限切れの取置を解除し、次の予約者がいれば取置を引き継がせるバッチ。

    本来は cron 等で定期実行する想定(lending の detect_overdue と同様、
    このサンプルには定期実行の仕組み自体は含まれていない)。
    """

    help = "Expire holds past their expiry date and promote the next reservation, if any."

    def handle(self, *args, **options):
        today = date.today()
        repository = DjangoReservationQueueRepository()
        use_case = ExpireHoldsUseCase(repository=repository)

        # 期限切れの取置を持つ書誌だけを対象にする(全書誌を舐めない)。
        title_ids = repository.titles_with_expired_holds(today)
        for title_id in title_ids:
            use_case.execute(title_id, today=today)

        self.stdout.write(
            self.style.SUCCESS(f"Processed {len(title_ids)} title(s) with expired holds.")
        )
