from rest_framework.response import Response
from rest_framework.views import APIView

from ordering.application.queries import list_orders
from ordering.presentation.serializers import OrderSerializer


# 参照側(CQRS の Q)の API。金額がドメイン層で計算されるため、ListAPIView ではなく
# queries.py が返す DTO をそのままシリアライズする(ADR-0003 の「ordering は未移行」)。


class OrderListAPIView(APIView):
    def get(self, request):
        return Response(OrderSerializer(list_orders(), many=True).data)
