import django_filters

from kitchen.infrastructure.models import TicketModel

# 参照 API の絞り込み条件(ADR-0003)。クエリパラメータ → QuerySet.filter() の変換を
# django-filter に任せ、条件ごとに queries.py へ関数を足していくのをやめる。
#   ?status=QUEUED&status=COOKING  … 状態で絞り込み(複数指定は OR)
#   ?order_id=<uuid>                … 注文 ID で 1 件を引く


class TicketFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=TicketModel.Status.choices)

    class Meta:
        model = TicketModel
        fields = ["status", "order_id"]
