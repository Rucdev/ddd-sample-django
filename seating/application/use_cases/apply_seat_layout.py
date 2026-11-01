from django.db import transaction

from seating.application.dto import ApplySeatLayoutResult
from seating.domain.repositories import AreaRepository, SeatRepository
from seating.domain.services import plan_layout_changes
from seating.domain.value_objects import SeatLayout


class ApplySeatLayoutUseCase:
    """座席構成(座席構成ファイルを読んだもの)を DB に反映する。

    `manage.py apply_seat_layout` から呼ばれる。何度流しても同じ結果になる(冪等)。
    席の追加・変更・撤去はすべて 1 トランザクションで行い、撤去できない席が 1 つでも
    あれば何も変えずに `SeatsInUse` を投げる。
    """

    def __init__(self, seat_repository: SeatRepository, area_repository: AreaRepository) -> None:
        self._seats = seat_repository
        self._areas = area_repository

    def execute(self, layout: SeatLayout) -> ApplySeatLayoutResult:
        with transaction.atomic():
            # 反映中に席のステータスが変わる(撤去しようとした席が予約される等)のを防ぐため、全席をロックする
            changes = plan_layout_changes(self._seats.find_all(for_update=True), layout)

            # 順番に意味がある: 撤去 → エリアを用意 → 席を保存 → 空いたエリアを消す。
            # 席がエリアを移るときに、移り先のエリアが先にあり、移り元のエリアが後で消えるように。
            for seat in changes.removed:
                self._seats.remove(seat)
            self._areas.save_all(layout.areas)
            for seat in (*changes.installed, *changes.changed):
                self._seats.save(seat)
            self._areas.remove_except(area.code for area in layout.areas)

        return ApplySeatLayoutResult(
            installed=tuple(seat.code for seat in changes.installed),
            changed=tuple(seat.code for seat in changes.changed),
            removed=tuple(seat.code for seat in changes.removed),
            unchanged=changes.unchanged,
        )
