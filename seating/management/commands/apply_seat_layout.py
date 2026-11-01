from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from seating.application.use_cases.apply_seat_layout import ApplySeatLayoutUseCase
from seating.domain.exceptions import SeatingError
from seating.infrastructure.layout_file import load_seat_layout
from seating.infrastructure.repositories import DjangoAreaRepository, DjangoSeatRepository


class Command(BaseCommand):
    """座席構成ファイルを読んで DB に反映する。画面・API と同じく、ユースケースを組み立てて
    呼ぶだけの presentation 層(入口が HTTP ではなくコマンドラインなだけ)。
    """

    help = "座席構成ファイル(YAML)を読み、席の追加・変更・撤去を DB に反映する"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            default=str(settings.SEAT_LAYOUT_FILE),
            help="座席構成ファイルのパス(既定: settings.SEAT_LAYOUT_FILE)",
        )

    def handle(self, *args, **options) -> None:
        use_case = ApplySeatLayoutUseCase(
            seat_repository=DjangoSeatRepository(),
            area_repository=DjangoAreaRepository(),
        )
        try:
            result = use_case.execute(load_seat_layout(options["file"]))
        except SeatingError as exc:
            raise CommandError(str(exc)) from exc

        for label, codes in (("追加", result.installed), ("変更", result.changed), ("撤去", result.removed)):
            if codes:
                self.stdout.write(f"{label}: {', '.join(codes)}")
        self.stdout.write(
            self.style.SUCCESS(
                f"座席構成を反映しました(追加 {len(result.installed)} / 変更 {len(result.changed)}"
                f" / 撤去 {len(result.removed)} / 変更なし {result.unchanged})"
            )
        )
