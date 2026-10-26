"""参照系(CQRS の Q)。リポジトリ/集約を経由せず ORM を直読みする。

チケットの参照には計算ルールが絡まないので、DTO への詰め替えもせず QuerySet をそのまま
返す。絞り込み・並び替えは presentation 層の FilterSet / DRF の ListAPIView に任せる
(ADR-0003)。QuerySet なので呼び出し側でさらに filter() を重ねてもクエリは 1 本のまま。
"""

from django.db.models import QuerySet

from kitchen.infrastructure.models import TicketModel


def ticket_queryset() -> QuerySet[TicketModel]:
    return TicketModel.objects.order_by("created_at")


def open_ticket_queryset() -> QuerySet[TicketModel]:
    """キッチン画面に出す「まだ手を動かす必要がある」チケット(調理待ち・調理中)。古い順。"""
    return ticket_queryset().filter(
        status__in=[TicketModel.Status.QUEUED, TicketModel.Status.COOKING]
    )
