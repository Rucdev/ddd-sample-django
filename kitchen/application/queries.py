"""参照系(CQRS の Q)。リポジトリ/集約を経由せず ORM を直読みする。

チケットは注文明細 1 行につき 1 枚。チケットの参照には計算ルールが絡まないので、DTO への詰め替えもせず QuerySet をそのまま
返す。絞り込み・並び替えは presentation 層の FilterSet / DRF の ListAPIView に任せる
(ADR-0003)。QuerySet なので呼び出し側でさらに filter() を重ねてもクエリは 1 本のまま。
"""

from django.db.models import Count, OuterRef, QuerySet, Subquery

from kitchen.infrastructure.models import TicketModel


def _with_order_line_count(queryset: QuerySet[TicketModel]) -> QuerySet[TicketModel]:
    """各チケットに「同じ注文のチケットが全部で何枚あるか」(`order_line_count`)を付ける。
    画面のカードに「2/3」と出し、同じ注文の残りがあることを分かるようにするため。
    """
    siblings = (
        TicketModel.objects.filter(order_id=OuterRef("order_id"))
        .values("order_id")
        .annotate(count=Count("id"))
        .values("count")
    )
    return queryset.annotate(order_line_count=Subquery(siblings))


def ticket_queryset() -> QuerySet[TicketModel]:
    # 同じ時刻に作られた同じ注文のチケットは、明細の順に並べる
    return _with_order_line_count(TicketModel.objects.order_by("created_at", "order_id", "line_no"))


def open_ticket_queryset() -> QuerySet[TicketModel]:
    """キッチン画面に出す「まだ手を動かす必要がある」チケット(調理待ち・調理中)。古い順。"""
    return ticket_queryset().filter(
        status__in=[TicketModel.Status.QUEUED, TicketModel.Status.COOKING]
    )


def recent_done_ticket_queryset(limit: int = 10) -> QuerySet[TicketModel]:
    """キッチン画面の「調理済」列に出す、直近に調理が終わったチケット。新しい順。"""
    return _with_order_line_count(
        TicketModel.objects.filter(status=TicketModel.Status.DONE).order_by("-created_at", "line_no")
    )[:limit]
