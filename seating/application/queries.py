"""参照系(CQRS の Q)。リポジトリ/集約を経由せず ORM を直読みする(kitchen と同じ方針。ADR-0003)。

席の参照には計算ルールが絡まないので QuerySet をそのまま返す。集計(空き何席・何人分など)は
数を数えるだけなので、ここで dict にまとめて返す。
"""

from dataclasses import dataclass

from django.db.models import Count, Prefetch, QuerySet, Sum

from seating.infrastructure.models import AreaModel, SeatModel


def seat_queryset() -> QuerySet[SeatModel]:
    return SeatModel.objects.select_related("area").order_by("area__display_order", "row", "col")


def area_queryset_with_seats() -> QuerySet[AreaModel]:
    """座席画面の見取り図用。エリアごとに席を位置順で持たせる(クエリは 2 本)。"""
    return AreaModel.objects.order_by("display_order").prefetch_related(
        Prefetch("seats", queryset=SeatModel.objects.order_by("row", "col"))
    )


@dataclass(frozen=True)
class StatusSummary:
    status: str
    label: str
    seats: int  # 席数
    capacity: int  # その席に座れる人数の合計


def status_summary() -> list[StatusSummary]:
    """ステータスごとの席数と人数。席が 1 つもないステータスも 0 で返す(画面の並びを固定するため)。"""
    rows = {
        row["status"]: row
        for row in SeatModel.objects.values("status").annotate(seats=Count("id"), capacity=Sum("capacity"))
    }
    return [
        StatusSummary(
            status=status.value,
            label=status.label,
            seats=rows.get(status.value, {}).get("seats", 0),
            capacity=rows.get(status.value, {}).get("capacity", 0),
        )
        for status in SeatModel.Status
    ]
