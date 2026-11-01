import django_filters

from seating.infrastructure.models import SeatModel

# 参照 API の絞り込み条件(ADR-0003)。
#   ?status=AVAILABLE&status=RESERVED  … ステータスで絞り込み(複数指定は OR)
#   ?area=terrace                      … エリアコードで絞り込み
#   ?min_capacity=4                    … 何人以上座れる席か


class SeatFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=SeatModel.Status.choices)
    area = django_filters.CharFilter(field_name="area__code")
    min_capacity = django_filters.NumberFilter(field_name="capacity", lookup_expr="gte")

    class Meta:
        model = SeatModel
        fields = ["status", "area", "min_capacity"]
