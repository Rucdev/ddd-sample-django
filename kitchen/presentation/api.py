from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.queries import ticket_queryset
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.infrastructure.repositories import DjangoTicketRepository
from kitchen.presentation.filters import TicketFilter
from kitchen.presentation.serializers import TicketSerializer


# コマンド側は ordering/presentation/api.py と同じく DRF を限定利用する(ADR-0001):
# APIView + 素の Serializer でユースケースを呼ぶだけ。
# 参照側はユースケースを通らないので、ListAPIView と django-filter を素直に使う(ADR-0003)。


class TicketListAPIView(ListAPIView):
    queryset = ticket_queryset()
    # コマンドの応答と同じ Serializer を使い、一覧と更新結果のレスポンス形を揃える。
    # 素の Serializer は属性を読むだけなので、DTO でも ORM モデルでもそのまま渡せる。
    serializer_class = TicketSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TicketFilter
    ordering_fields = ["created_at"]


class StartCookingAPIView(APIView):
    def post(self, request, ticket_id):
        use_case = StartCookingUseCase(repository=DjangoTicketRepository())
        result = use_case.execute(StartCookingInput(ticket_id=ticket_id))
        return Response(TicketSerializer(result).data)


class CompleteCookingAPIView(APIView):
    def post(self, request, ticket_id):
        use_case = CompleteCookingUseCase(repository=DjangoTicketRepository())
        result = use_case.execute(CompleteCookingInput(ticket_id=ticket_id))
        return Response(TicketSerializer(result).data)
