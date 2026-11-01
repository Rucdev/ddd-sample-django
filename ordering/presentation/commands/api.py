from rest_framework.response import Response
from rest_framework.views import APIView

from ordering.application.dto import (
    CancelOrderInput,
    PickUpOrderInput,
    PlaceOrderInput,
    PlaceOrderLineInput,
    PlaceSeatOrderInput,
    ServeOrderInput,
)
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.application.use_cases.place_seat_order import PlaceSeatOrderUseCase
from ordering.application.use_cases.serve_order import ServeOrderUseCase
from ordering.infrastructure.repositories import DjangoBillRepository, DjangoOrderRepository
from ordering.presentation.serializers import (
    OrderSerializer,
    PlaceOrderSerializer,
    PlaceSeatOrderSerializer,
)


# コマンド側(CQRS の C)の API。DDD アプリでの DRF の使い方(ADR-0001): APIView と素の
# Serializer だけを使う。ModelSerializer / ModelViewSet は ORM モデルと API を直結させ、
# ユースケースを迂回してしまうため使わない(CRUD アプリでは逆に主力として使ってよい)。
# ドメイン例外 → HTTP ステータスの変換は shared/infrastructure/exception_handler.py に一元化。


class PlaceOrderAPIView(APIView):
    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        use_case = PlaceOrderUseCase(order_repository=DjangoOrderRepository())
        result = use_case.execute(
            PlaceOrderInput(
                customer_id=data["customer_id"],
                lines=tuple(PlaceOrderLineInput(**line) for line in data["lines"]),
            )
        )
        return Response(OrderSerializer(result).data, status=201)


class CancelOrderAPIView(APIView):
    def post(self, request, order_id):
        use_case = CancelOrderUseCase(order_repository=DjangoOrderRepository())
        result = use_case.execute(CancelOrderInput(order_id=order_id))
        return Response(OrderSerializer(result).data)


class PickUpOrderAPIView(APIView):
    def post(self, request, order_id):
        use_case = PickUpOrderUseCase(order_repository=DjangoOrderRepository())
        result = use_case.execute(PickUpOrderInput(order_id=order_id))
        return Response(OrderSerializer(result).data)


class PlaceSeatOrderAPIView(APIView):
    """席からの注文(店内)。会員 ID は要らない。"""

    def post(self, request, seat_id):
        serializer = PlaceSeatOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = PlaceSeatOrderUseCase(
            order_repository=DjangoOrderRepository(), bill_repository=DjangoBillRepository()
        )
        result = use_case.execute(
            PlaceSeatOrderInput(
                seat_id=seat_id,
                lines=tuple(PlaceOrderLineInput(**line) for line in serializer.validated_data["lines"]),
            )
        )
        return Response(OrderSerializer(result).data, status=201)


class ServeOrderAPIView(APIView):
    def post(self, request, order_id):
        use_case = ServeOrderUseCase(order_repository=DjangoOrderRepository())
        result = use_case.execute(ServeOrderInput(order_id=order_id))
        return Response(OrderSerializer(result).data)
