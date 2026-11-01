from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from ordering.application.queries import get_open_bill_for_seat, list_orders
from ordering.presentation.serializers import BillSerializer, OrderSerializer


# 参照側(CQRS の Q)の API。金額がドメイン層で計算されるため、ListAPIView ではなく
# queries.py が返す DTO をそのままシリアライズする(ADR-0003 の「ordering は未移行」)。


class OrderListAPIView(APIView):
    def get(self, request):
        return Response(OrderSerializer(list_orders(), many=True).data)


class SeatBillAPIView(APIView):
    """その席でいま開いている会計(注文の明細と金額)。席が使用中でなければ 404。"""

    def get(self, request, seat_id):
        bill = get_open_bill_for_seat(seat_id)
        if bill is None:
            raise Http404("This seat has no open bill")
        return Response(BillSerializer(bill).data)
