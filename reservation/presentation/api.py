from rest_framework.response import Response
from rest_framework.views import APIView

from reservation.application.dto import CancelReservationInput, ReserveTitleInput
from reservation.application.queries import list_reservations
from reservation.application.use_cases.cancel_reservation import CancelReservationUseCase
from reservation.application.use_cases.reserve_title import ReserveTitleUseCase
from reservation.infrastructure.repositories import DjangoReservationQueueRepository
from reservation.presentation.serializers import ReservationSerializer, ReserveTitleSerializer


# lending/presentation/api.py と同じく DRF は限定利用(ADR-0001): APIView + 素の
# Serializer のみ。ModelSerializer / ModelViewSet は使わない。


class ReservationListCreateAPIView(APIView):
    def get(self, request):
        return Response(ReservationSerializer(list_reservations(), many=True).data)

    def post(self, request):
        serializer = ReserveTitleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = ReserveTitleUseCase(repository=DjangoReservationQueueRepository())
        result = use_case.execute(ReserveTitleInput(**serializer.validated_data))
        return Response(ReservationSerializer(result).data, status=201)


class ReservationCancelAPIView(APIView):
    def delete(self, request, title_id, member_id):
        use_case = CancelReservationUseCase(repository=DjangoReservationQueueRepository())
        use_case.execute(CancelReservationInput(member_id=member_id, title_id=title_id))
        return Response(status=204)
