from collections.abc import Iterable
from dataclasses import dataclass

from seating.domain.entities import Seat
from seating.domain.exceptions import SeatsInUse
from seating.domain.value_objects import SeatLayout


@dataclass(frozen=True)
class LayoutChanges:
    """座席構成ファイルを DB に反映するときの差分。"""

    installed: tuple[Seat, ...]  # ファイルに新しく現れた席
    changed: tuple[Seat, ...]  # エリア・定員・位置が変わった席(ステータスは保つ)
    removed: tuple[Seat, ...]  # ファイルから消えた席
    unchanged: int


def plan_layout_changes(current: Iterable[Seat], layout: SeatLayout) -> LayoutChanges:
    """いまの座席と新しい座席構成を席コードで突き合わせ、差分を作るドメインサービス。

    席の同一性は席コードで判定する(コードを変えると「撤去して新設」になる)。撤去する席が
    予約中・使用中なら、お客様を置き去りにしないよう構成の反映ごと断る。
    """
    current_by_code = {seat.code: seat for seat in current}

    in_use = [
        seat.code
        for code, seat in current_by_code.items()
        if layout.seat(code) is None and not seat.is_removable
    ]
    if in_use:
        raise SeatsInUse(in_use)

    installed: list[Seat] = []
    changed: list[Seat] = []
    unchanged = 0
    for spec in layout.seats:
        seat = current_by_code.get(spec.code)
        if seat is None:
            installed.append(Seat.install(spec))
        elif seat.matches(spec):
            unchanged += 1
        else:
            seat.apply_spec(spec)
            changed.append(seat)

    removed = [seat for code, seat in current_by_code.items() if layout.seat(code) is None]
    return LayoutChanges(
        installed=tuple(installed),
        changed=tuple(changed),
        removed=tuple(removed),
        unchanged=unchanged,
    )
