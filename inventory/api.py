from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from inventory import services
from inventory.models import Kit, Reservation, StockMovement
from inventory.serializers import (
    IssueSerializer,
    KitSerializer,
    QuantitySerializer,
    ReservationSerializer,
    StockMovementSerializer,
)

# CRUD アプリなので ViewSet + ルーターを使う(ADR-0001)。ただし在庫数を動かす操作は
# 汎用の update ではなく @action にし、services.py を呼んでログを書く。
# 削除はどれも提供しない(在庫ログを残すため)。


class KitViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Kit.objects.all()
    serializer_class = KitSerializer
    lookup_value_converter = "uuid"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "menu_item_id"]

    def _apply(self, request, serializer_class, operation):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        kit = operation(serializer.validated_data)
        return Response(KitSerializer(kit).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk):
        return self._apply(
            request, QuantitySerializer, lambda data: services.receive(pk, data["quantity"], data["memo"])
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk):
        return self._apply(
            request, IssueSerializer, lambda data: services.issue(pk, data["quantity"], data["memo"])
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk):
        return Response(KitSerializer(services.deactivate_kit(pk)).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk):
        return Response(KitSerializer(services.activate_kit(pk)).data)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    lookup_value_converter = "uuid"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "kit"]

    @action(detail=True, methods=["post"])
    def use(self, request, pk):
        return Response(ReservationSerializer(services.use_reservation(pk)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk):
        return Response(ReservationSerializer(services.cancel_reservation(pk)).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    lookup_value_converter = "uuid"
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["kind", "kit", "order_id"]
    ordering_fields = ["created_at"]
