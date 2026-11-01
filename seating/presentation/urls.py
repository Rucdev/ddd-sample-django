from django.urls import path

from seating.presentation import api, views

# app_name で名前空間化し、config/urls.py から include() で束ねる。
app_name = "seating"

urlpatterns = [
    path("", views.seat_board_view, name="seat_board"),
    path("<uuid:seat_id>/reserve/", views.reserve_seat_view, name="reserve"),
    path("<uuid:seat_id>/cancel-reservation/", views.cancel_reservation_view, name="cancel_reservation"),
    path("<uuid:seat_id>/occupy/", views.occupy_seat_view, name="occupy"),
    path("<uuid:seat_id>/vacate/", views.vacate_seat_view, name="vacate"),
    path("api/seats/", api.SeatListAPIView.as_view(), name="api_seat_list"),
    path("api/seats/<uuid:seat_id>/reserve/", api.ReserveSeatAPIView.as_view(), name="api_reserve"),
    path(
        "api/seats/<uuid:seat_id>/cancel-reservation/",
        api.CancelSeatReservationAPIView.as_view(),
        name="api_cancel_reservation",
    ),
    path("api/seats/<uuid:seat_id>/occupy/", api.OccupySeatAPIView.as_view(), name="api_occupy"),
    path("api/seats/<uuid:seat_id>/vacate/", api.VacateSeatAPIView.as_view(), name="api_vacate"),
]
