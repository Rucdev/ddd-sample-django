from django.urls import path

from reservation.presentation import api, views

# app_name で名前空間化し、config/urls.py から include() で束ねる。
app_name = "reservation"

urlpatterns = [
    path("", views.reservation_list_view, name="reservation_list"),
    path("reserve/", views.reserve_title_view, name="reserve_title"),
    path(
        "<uuid:title_id>/<uuid:member_id>/cancel/",
        views.cancel_reservation_view,
        name="cancel_reservation",
    ),
    path(
        "api/reservations/",
        api.ReservationListCreateAPIView.as_view(),
        name="api_reservation_list",
    ),
    path(
        "api/reservations/<uuid:title_id>/<uuid:member_id>/",
        api.ReservationCancelAPIView.as_view(),
        name="api_reservation_cancel",
    ),
]
