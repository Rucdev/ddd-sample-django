from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from seating.application.dto import SeatCommandInput
from seating.application.queries import seat_queryset
from seating.application.use_cases.change_seat_status import (
    CancelSeatReservationUseCase,
    OccupySeatUseCase,
    ReserveSeatUseCase,
    VacateSeatUseCase,
)
from seating.infrastructure.repositories import DjangoSeatRepository
from seating.presentation.filters import SeatFilter
from seating.presentation.serializers import SeatModelSerializer, SeatSerializer

# kitchen/presentation/api.py と同じ方針: コマンド側は APIView + 素の Serializer で
# ユースケースを呼ぶだけ(ADR-0001)。参照側は ListAPIView と django-filter(ADR-0003)。


class SeatListAPIView(ListAPIView):
    queryset = seat_queryset()
    serializer_class = SeatModelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SeatFilter


class _SeatCommandAPIView(APIView):
    use_case_class: type[ReserveSeatUseCase]

    def post(self, request, seat_id):
        use_case = self.use_case_class(repository=DjangoSeatRepository())
        result = use_case.execute(SeatCommandInput(seat_id=seat_id))
        return Response(SeatSerializer(result).data)


class ReserveSeatAPIView(_SeatCommandAPIView):
    use_case_class = ReserveSeatUseCase


class CancelSeatReservationAPIView(_SeatCommandAPIView):
    use_case_class = CancelSeatReservationUseCase


class OccupySeatAPIView(_SeatCommandAPIView):
    use_case_class = OccupySeatUseCase


class VacateSeatAPIView(_SeatCommandAPIView):
    use_case_class = VacateSeatUseCase
